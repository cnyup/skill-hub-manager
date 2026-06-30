import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from skill_hub_manager import __version__
from skill_hub_manager.agents import detect_agent_target
from skill_hub_manager.audit import audit_profiles, render_audit_json
from skill_hub_manager.doctor import find_broken_links, find_missing_expected_links, load_sync_target
from skill_hub_manager.install_state import (
    find_install_record,
    load_install_records,
    upsert_install_record,
    write_install_records,
)
from skill_hub_manager.paths import (
    initialize_workspace,
    install_state_file,
    resolve_workspace_root,
    workspace_paths,
)
from skill_hub_manager.profiles import (
    Profile,
    clone_profile,
    list_profiles,
    load_profile,
    render_profile_validation_json,
    remove_profile,
    rename_profile,
    update_profile,
    validate_profile,
    write_profile,
)
from skill_hub_manager.registry import (
    doctor_registry,
    find_registry_entries,
    load_registry_entries,
    render_registry_doctor_json,
    render_registry_entries_json,
    write_registry,
)
from skill_hub_manager.skills import scan_skills
from skill_hub_manager.sync import render_sync_result_json, sync_profile, write_sync_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-hub")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    agent = subparsers.add_parser("agent")
    agent_subparsers = agent.add_subparsers(dest="agent_command")

    agent_detect = agent_subparsers.add_parser("detect")
    agent_detect.add_argument("--root", required=True)
    agent_detect.add_argument("--agent")
    agent_detect.add_argument("--json", action="store_true")

    scan = subparsers.add_parser("scan")
    scan.add_argument("--vault")
    scan.add_argument("--root")

    ls_cmd = subparsers.add_parser("ls")
    ls_cmd.add_argument("--root", required=True)
    ls_cmd.add_argument("--json", action="store_true")

    find_cmd = subparsers.add_parser("find")
    find_cmd.add_argument("--root", required=True)
    find_cmd.add_argument("--query", required=True)
    find_cmd.add_argument("--json", action="store_true")

    audit_cmd = subparsers.add_parser("audit")
    audit_cmd.add_argument("--root", required=True)
    audit_cmd.add_argument("--json", action="store_true")

    init = subparsers.add_parser("init")
    init.add_argument("--root", required=True)

    registry = subparsers.add_parser("registry")
    registry_subparsers = registry.add_subparsers(dest="registry_command")
    registry_build = registry_subparsers.add_parser("build")
    registry_build.add_argument("--vault")
    registry_build.add_argument("--output")
    registry_build.add_argument("--root")

    registry_doctor = registry_subparsers.add_parser("doctor")
    registry_doctor.add_argument("--vault")
    registry_doctor.add_argument("--output")
    registry_doctor.add_argument("--root")
    registry_doctor.add_argument("--json", action="store_true")
    registry_doctor.add_argument("--rebuild-if-drift", action="store_true")

    sync = subparsers.add_parser("sync")
    sync.add_argument("--vault")
    sync.add_argument("--profile")
    sync.add_argument("--root")
    sync.add_argument("--target", required=True)
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--json", action="store_true")

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--target")
    doctor.add_argument("--root")

    install_state = subparsers.add_parser("install-state")
    install_state_subparsers = install_state.add_subparsers(dest="install_state_command")

    install_state_show = install_state_subparsers.add_parser("show")
    install_state_show.add_argument("--root", required=True)
    install_state_show.add_argument("--agent")
    install_state_show.add_argument("--json", action="store_true")

    install_state_record = install_state_subparsers.add_parser("record")
    install_state_record.add_argument("--root", required=True)
    install_state_record.add_argument("--agent", required=True)
    install_state_record.add_argument("--profile", required=True)
    install_state_record.add_argument("--target", required=True)
    install_state_record.add_argument("--manager-path", required=True)
    install_state_record.add_argument("--manager-repo", required=True)
    install_state_record.add_argument("--manager-revision", required=True)
    install_state_record.add_argument("--detection-confidence", required=True)
    install_state_record.add_argument("--detection-reason", required=True)

    profile = subparsers.add_parser("profile")
    profile_subparsers = profile.add_subparsers(dest="profile_command")

    profile_list = profile_subparsers.add_parser("list")
    profile_list.add_argument("--root", required=True)

    profile_show = profile_subparsers.add_parser("show")
    profile_show.add_argument("--root", required=True)
    profile_show.add_argument("--name", required=True)

    profile_add = profile_subparsers.add_parser("add")
    profile_add.add_argument("--root", required=True)
    profile_add.add_argument("--name", required=True)
    profile_add.add_argument("--agent", required=True)
    profile_add.add_argument("--skill", action="append", required=True)
    profile_add.add_argument("--exclude", action="append", default=[])

    profile_remove = profile_subparsers.add_parser("remove")
    profile_remove.add_argument("--root", required=True)
    profile_remove.add_argument("--name", required=True)

    profile_update = profile_subparsers.add_parser("update")
    profile_update.add_argument("--root", required=True)
    profile_update.add_argument("--name", required=True)
    profile_update.add_argument("--agent")
    profile_update.add_argument("--add-skill", action="append", default=[])
    profile_update.add_argument("--remove-skill", action="append", default=[])
    profile_update.add_argument("--add-exclude", action="append", default=[])
    profile_update.add_argument("--remove-exclude", action="append", default=[])

    profile_clone = profile_subparsers.add_parser("clone")
    profile_clone.add_argument("--root", required=True)
    profile_clone.add_argument("--name", required=True)
    profile_clone.add_argument("--to", required=True)

    profile_rename = profile_subparsers.add_parser("rename")
    profile_rename.add_argument("--root", required=True)
    profile_rename.add_argument("--name", required=True)
    profile_rename.add_argument("--to", required=True)

    profile_validate = profile_subparsers.add_parser("validate")
    profile_validate.add_argument("--root", required=True)
    profile_validate.add_argument("--name")
    profile_validate.add_argument("--json", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"skill-hub {__version__}")
        return 0
    if args.command == "agent" and args.agent_command == "detect":
        root = resolve_workspace_root(_optional_path(args.root))
        result = detect_agent_target(root=root, agent_hint=args.agent)
        payload = _render_detection_payload(result)
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        print(f"agent={payload['agent']}")
        print(f"detected={payload['detected']}")
        print(f"confidence={payload['confidence']}")
        print(f"target_dir={payload['target_dir']}")
        print(f"reason={payload['reason']}")
        return 0
    if args.command == "scan":
        for name in scan_skills(_resolve_scan_vault(args)):
            print(name)
        return 0
    if args.command == "ls":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        entries = load_registry_entries(paths.state / "registry.yaml")
        if args.json:
            print(render_registry_entries_json(entries))
            return 0
        for entry in entries:
            print(entry["name"])
        return 0
    if args.command == "find":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        entries = load_registry_entries(paths.state / "registry.yaml")
        matches = find_registry_entries(entries, args.query)
        if args.json:
            print(render_registry_entries_json(matches))
            return 0
        for entry in matches:
            print(entry["name"])
        return 0
    if args.command == "audit":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        reports = audit_profiles(paths.profiles, paths.skills)
        if args.json:
            print(render_audit_json(reports))
            return 0
        for report in reports:
            print(f"profile: {report['profile']}")
            print(f"agent: {report['agent']}")
            print(f"effective_skills: [{', '.join(report['effective_skills'])}]")
            print(f"missing_skills: [{', '.join(report['missing_skills'])}]")
        return 0
    if args.command == "init":
        paths = initialize_workspace(Path(args.root))
        print(f"initialized: {paths.root}")
        return 0
    if args.command == "registry" and args.registry_command == "build":
        vault, output_path = _resolve_registry_paths(args)
        output = write_registry(vault, output_path)
        print(f"wrote: {output}")
        return 0
    if args.command == "registry" and args.registry_command == "doctor":
        vault, output_path = _resolve_registry_paths(args)
        issues = doctor_registry(vault, output_path)
        if issues and args.rebuild_if_drift:
            output = write_registry(vault, output_path)
            if args.json:
                print(render_registry_doctor_json([]))
                return 0
            print(f"rebuilt: {output}")
            return 0
        if args.json:
            print(render_registry_doctor_json(issues))
            return 1 if issues else 0
        if not issues:
            print("ok: registry")
            return 0
        for issue in issues:
            print(issue)
        return 1
    if args.command == "sync":
        vault, profile_path = _resolve_sync_paths(args)
        profile = load_profile(profile_path)
        target = Path(args.target)
        result = sync_profile(profile, scan_skills(vault), target, dry_run=args.dry_run)
        if args.root and not args.dry_run:
            paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
            write_sync_state(
                paths.state / "last-sync.json",
                profile,
                target,
                result.linked,
                result.missing,
                result.removed,
            )
        if args.json:
            print(
                render_sync_result_json(
                    profile=profile,
                    target=target,
                    linked=result.linked,
                    missing=result.missing,
                    removed=result.removed,
                    dry_run=args.dry_run,
                )
            )
            return 1 if result.missing else 0
        if args.dry_run:
            for name in result.linked:
                print(f"would-link: {name}")
            for name in result.missing:
                print(f"would-miss: {name}")
            for name in result.removed:
                print(f"would-remove: {name}")
            return 1 if result.missing else 0
        for name in result.linked:
            print(f"linked: {name}")
        for name in result.missing:
            print(f"missing: {name}")
        for name in result.removed:
            print(f"removed: {name}")
        return 1 if result.missing else 0
    if args.command == "doctor":
        target = _resolve_doctor_target(args)
        broken = find_broken_links(target)
        expected_missing = _resolve_expected_missing(args, target)
        for name in broken:
            print(f"broken: {name}")
        for name in expected_missing:
            print(f"expected-missing: {name}")
        return 1 if broken or expected_missing else 0
    if args.command == "install-state" and args.install_state_command == "show":
        root = resolve_workspace_root(_optional_path(args.root))
        state_file = install_state_file(root)
        records = load_install_records(state_file)
        matched_record = find_install_record(records, args.agent) if args.agent else None
        matched_records = records if not args.agent else ([matched_record] if matched_record else [])
        payload = {
            "state_file": str(state_file),
            "records": matched_records,
            "record": matched_record if args.agent else None,
        }
        if args.agent and not matched_records:
            if args.json:
                print(json.dumps(payload, indent=2))
            else:
                print(f"missing: {args.agent}")
            return 1
        if args.json:
            print(json.dumps(payload, indent=2))
            return 0
        for record in matched_records:
            _print_install_record(record)
            print()
        return 0
    if args.command == "install-state" and args.install_state_command == "record":
        root = resolve_workspace_root(_optional_path(args.root))
        state_file = install_state_file(root)
        records = load_install_records(state_file)
        record = {
            "agent": args.agent,
            "profile": args.profile,
            "target_dir": args.target,
            "manager_path": args.manager_path,
            "manager_repo": args.manager_repo,
            "manager_revision": args.manager_revision,
            "installed_at": _utc_now(),
            "detection_confidence": args.detection_confidence,
            "detection_reason": args.detection_reason,
        }
        write_install_records(state_file, upsert_install_record(records, record))
        print(f"recorded: {state_file}")
        return 0
    if args.command == "profile" and args.profile_command == "list":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        for path in list_profiles(paths.profiles):
            print(path.stem)
        return 0
    if args.command == "profile" and args.profile_command == "show":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        profile = load_profile(paths.profiles / f"{args.name}.yaml")
        print(f"name: {profile.name}")
        print(f"agent: {profile.agent}")
        print(f"skills: [{', '.join(profile.skills)}]")
        print(f"exclude: [{', '.join(profile.exclude)}]")
        print(f"effective_skills: [{', '.join(profile.effective_skills())}]")
        return 0
    if args.command == "profile" and args.profile_command == "add":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        try:
            path = write_profile(
                paths.profiles,
                Profile(
                    name=args.name,
                    agent=args.agent,
                    skills=args.skill,
                    exclude=args.exclude,
                ),
            )
        except FileExistsError as error:
            print(f"exists: {error.args[0]}")
            return 1
        print(f"wrote: {path}")
        return 0
    if args.command == "profile" and args.profile_command == "remove":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        removed = remove_profile(paths.profiles, args.name)
        if removed:
            print(f"removed: {paths.profiles / f'{args.name}.yaml'}")
            return 0
        print(f"missing: {paths.profiles / f'{args.name}.yaml'}")
        return 1
    if args.command == "profile" and args.profile_command == "update":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        path = paths.profiles / f"{args.name}.yaml"
        profile = load_profile(path)
        updated = update_profile(
            profile,
            agent=args.agent,
            add_skills=args.add_skill,
            remove_skills=args.remove_skill,
            add_exclude=args.add_exclude,
            remove_exclude=args.remove_exclude,
        )
        write_profile(paths.profiles, updated, overwrite=True)
        print(f"updated: {path}")
        return 0
    if args.command == "profile" and args.profile_command == "clone":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        try:
            path = clone_profile(paths.profiles, args.name, args.to)
        except FileExistsError as error:
            print(f"exists: {error.args[0]}")
            return 1
        print(f"cloned: {path}")
        return 0
    if args.command == "profile" and args.profile_command == "rename":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        try:
            path = rename_profile(paths.profiles, args.name, args.to)
        except FileExistsError as error:
            print(f"exists: {error.args[0]}")
            return 1
        print(f"renamed: {path}")
        return 0
    if args.command == "profile" and args.profile_command == "validate":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        available_skills = set(scan_skills(paths.skills))
        profile_paths = (
            [paths.profiles / f"{args.name}.yaml"]
            if args.name
            else list_profiles(paths.profiles)
        )
        has_issues = False
        results: list[dict[str, str | bool | list[str]]] = []
        for profile_path in profile_paths:
            profile = load_profile(profile_path)
            issues = validate_profile(profile, available_skills)
            results.append(
                {
                    "profile": profile.name,
                    "valid": not issues,
                    "issues": issues,
                }
            )
            if issues:
                has_issues = True
                if args.json:
                    continue
                print(f"profile: {profile.name}")
                for issue in issues:
                    print(issue)
                continue
            if args.json:
                continue
            print(f"ok: {profile.name}")
        if args.json:
            print(render_profile_validation_json(results))
        return 1 if has_issues else 0
    parser.print_help()
    return 0


def _resolve_scan_vault(args: argparse.Namespace) -> Path:
    if args.vault:
        return Path(args.vault)
    return workspace_paths(resolve_workspace_root(_optional_path(args.root))).skills


def _resolve_registry_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.vault and args.output:
        return Path(args.vault), Path(args.output)
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    vault = Path(args.vault) if args.vault else paths.skills
    output = Path(args.output) if args.output else paths.state / "registry.yaml"
    return vault, output


def _resolve_sync_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.vault and args.profile:
        return Path(args.vault), Path(args.profile)
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    vault = Path(args.vault) if args.vault else paths.skills
    profile = Path(args.profile) if args.profile else paths.profiles / "default.yaml"
    return vault, profile


def _resolve_doctor_target(args: argparse.Namespace) -> Path:
    if args.target:
        return Path(args.target)
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    state_target = load_sync_target(paths.state / "last-sync.json")
    return state_target if state_target is not None else paths.skills


def _resolve_expected_missing(args: argparse.Namespace, target: Path) -> list[str]:
    if not args.root:
        return []
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    return find_missing_expected_links(target, paths.state / "last-sync.json")


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _render_detection_payload(result) -> dict[str, str | bool | None]:
    return {
        "agent": result.agent,
        "detected": result.detected,
        "confidence": result.confidence,
        "target_dir": None if result.target_dir is None else str(result.target_dir),
        "reason": result.reason,
    }


def _print_install_record(record: dict[str, str]) -> None:
    print(f"agent: {record.get('agent')}")
    print(f"profile: {record.get('profile')}")
    print(f"target_dir: {record.get('target_dir')}")
    print(f"manager_path: {record.get('manager_path')}")
    print(f"manager_repo: {record.get('manager_repo')}")
    print(f"manager_revision: {record.get('manager_revision')}")
    print(f"installed_at: {record.get('installed_at')}")
    print(f"detection_confidence: {record.get('detection_confidence')}")
    print(f"detection_reason: {record.get('detection_reason')}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
