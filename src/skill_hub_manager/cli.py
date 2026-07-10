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
from skill_hub_manager.importer import import_skill_directory, remove_skill_directory
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
from skill_hub_manager.source_state import (
    find_source_record,
    load_source_records,
    remove_source_record,
    upsert_source_record,
    write_source_records,
)
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
    scan.add_argument("--json", action="store_true")

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

    skill = subparsers.add_parser("skill")
    skill_subparsers = skill.add_subparsers(dest="skill_command")

    skill_import = skill_subparsers.add_parser("import")
    skill_import.add_argument("--root", required=True)
    skill_import.add_argument("--source", required=True)
    skill_import.add_argument("--name")
    skill_import.add_argument("--force", action="store_true")
    skill_import.add_argument("--source-ref")
    skill_import.add_argument("--source-type")
    skill_import.add_argument("--repo-url")
    skill_import.add_argument("--git-ref")
    skill_import.add_argument("--cache-checkout")
    skill_import.add_argument("--import-subpath")
    skill_import.add_argument("--json", action="store_true")

    skill_remove = skill_subparsers.add_parser("remove")
    skill_remove.add_argument("--root", required=True)
    skill_remove.add_argument("--name", required=True)
    skill_remove.add_argument("--purge-source", action="store_true")
    skill_remove.add_argument("--json", action="store_true")

    skill_update = skill_subparsers.add_parser("update")
    skill_update.add_argument("--root", required=True)
    skill_update.add_argument("--name", required=True)
    skill_update.add_argument("--json", action="store_true")

    skill_source = skill_subparsers.add_parser("source")
    skill_source_subparsers = skill_source.add_subparsers(dest="skill_source_command")

    skill_source_list = skill_source_subparsers.add_parser("list")
    skill_source_list.add_argument("--root", required=True)
    skill_source_list.add_argument("--json", action="store_true")

    skill_source_show = skill_source_subparsers.add_parser("show")
    skill_source_show.add_argument("--root", required=True)
    skill_source_show.add_argument("--name", required=True)
    skill_source_show.add_argument("--json", action="store_true")

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


def _cmd_agent_detect(args: argparse.Namespace) -> int:
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


def _cmd_scan(args: argparse.Namespace) -> int:
    names = sorted(scan_skills(_resolve_scan_vault(args)).keys())
    if args.json:
        print(json.dumps({"skills": names}, indent=2))
        return 0
    for name in names:
        print(name)
    return 0


def _cmd_ls(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    entries = load_registry_entries(paths.state / "registry.yaml")
    if args.json:
        print(render_registry_entries_json(entries))
        return 0
    for entry in entries:
        print(entry["name"])
    return 0


def _cmd_find(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    entries = load_registry_entries(paths.state / "registry.yaml")
    matches = find_registry_entries(entries, args.query)
    if args.json:
        print(render_registry_entries_json(matches))
        return 0
    for entry in matches:
        print(entry["name"])
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
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


def _cmd_init(args: argparse.Namespace) -> int:
    paths = initialize_workspace(Path(args.root))
    print(f"initialized: {paths.root}")
    return 0


def _cmd_registry_build(args: argparse.Namespace) -> int:
    vault, output_path = _resolve_registry_paths(args)
    output = write_registry(vault, output_path)
    print(f"wrote: {output}")
    return 0


def _cmd_registry_doctor(args: argparse.Namespace) -> int:
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


def _cmd_sync(args: argparse.Namespace) -> int:
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


def _cmd_doctor(args: argparse.Namespace) -> int:
    target = _resolve_doctor_target(args)
    broken = find_broken_links(target)
    expected_missing = _resolve_expected_missing(args, target)
    for name in broken:
        print(f"broken: {name}")
    for name in expected_missing:
        print(f"expected-missing: {name}")
    return 1 if broken or expected_missing else 0


def _cmd_install_state_show(args: argparse.Namespace) -> int:
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


def _cmd_install_state_record(args: argparse.Namespace) -> int:
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


def _cmd_skill_import(args: argparse.Namespace) -> int:
    paths = initialize_workspace(resolve_workspace_root(_optional_path(args.root)))
    source = Path(args.source)
    try:
        result = import_skill_directory(
            source=source,
            destination_root=paths.skills,
            skill_name=args.name,
            overwrite=args.force,
        )
    except ValueError as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "skill": args.name or Path(args.source).name,
                        "source": str(source),
                        "target": str(paths.skills / (args.name or Path(args.source).name)),
                        "replaced": False,
                        "state_file": str(paths.state / "skill-sources.json"),
                        "error": str(error),
                    },
                    indent=2,
                )
            )
        else:
            print(str(error))
        return 1
    except FileExistsError as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "skill": args.name or Path(args.source).name,
                        "source": str(source),
                        "target": str(error.args[0]),
                        "replaced": False,
                        "state_file": str(paths.state / "skill-sources.json"),
                        "error": f"exists: {error.args[0]}",
                    },
                    indent=2,
                )
            )
        else:
            print(f"exists: {error.args[0]}")
        return 1
    source_state_path = paths.state / "skill-sources.json"
    records = load_source_records(source_state_path)
    record = {
        "skill": result.skill,
        "source": args.source_ref or str(result.source),
        "stored_path": str(result.target),
        "imported_at": _utc_now(),
    }
    if args.source_type:
        record["source_type"] = args.source_type
    if args.repo_url:
        record["repo_url"] = args.repo_url
    if args.git_ref:
        record["git_ref"] = args.git_ref
    if args.cache_checkout:
        record["cache_checkout"] = args.cache_checkout
    if args.import_subpath:
        record["import_subpath"] = args.import_subpath
    write_source_records(source_state_path, upsert_source_record(records, record))
    if args.json:
        print(
            json.dumps(
                {
                    "skill": result.skill,
                    "source": str(result.source),
                    "target": str(result.target),
                    "replaced": result.replaced,
                    "state_file": str(source_state_path),
                },
                indent=2,
            )
        )
        return 0
    print(f"imported: {result.skill}")
    print(f"source: {result.source}")
    print(f"target: {result.target}")
    print(f"replaced: {'yes' if result.replaced else 'no'}")
    print(f"recorded: {source_state_path}")
    return 0


def _cmd_skill_remove(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    result = remove_skill_directory(paths.skills, args.name)
    if not result.removed:
        if args.json:
            print(
                json.dumps(
                    {
                        "skill": args.name,
                        "target": str(result.target),
                        "removed": False,
                    },
                    indent=2,
                )
            )
        else:
            print(f"missing: {args.name}")
        return 1
    source_state_path = paths.state / "skill-sources.json"
    if args.purge_source:
        records = remove_source_record(load_source_records(source_state_path), args.name)
        write_source_records(source_state_path, records)
    profiles_dir = paths.profiles
    updated_profiles: list[str] = []
    for profile_path in list_profiles(profiles_dir):
        profile = load_profile(profile_path)
        if args.name in profile.skills:
            updated = update_profile(profile, remove_skills=[args.name])
            write_profile(profiles_dir, updated, overwrite=True)
            updated_profiles.append(profile.name)
    write_registry(paths.skills, paths.state / "registry.yaml")
    if args.json:
        print(
            json.dumps(
                {
                    "skill": args.name,
                    "target": str(result.target),
                    "removed": True,
                    "purged_source": args.purge_source,
                    "updated_profiles": updated_profiles,
                },
                indent=2,
            )
        )
        return 0
    print(f"removed: {args.name}")
    if updated_profiles:
        print(f"updated_profiles: {', '.join(updated_profiles)}")
    print("rebuilt: registry")
    return 0


def _cmd_skill_update(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    source_state_path = paths.state / "skill-sources.json"
    records = load_source_records(source_state_path)
    record = find_source_record(records, args.name)
    if record is None:
        if args.json:
            print(json.dumps({"skill": args.name, "updated": False, "error": "no source record"}, indent=2))
        else:
            print(f"no source record: {args.name}")
        return 1

    cache_checkout = record.get("cache_checkout") or record.get("source")
    if not cache_checkout:
        if args.json:
            print(json.dumps({"skill": args.name, "updated": False, "error": "no cached source path"}, indent=2))
        else:
            print(f"no cached source path for: {args.name}")
        return 1

    import_source = Path(cache_checkout)
    import_subpath = record.get("import_subpath")
    if import_subpath:
        import_source = import_source / import_subpath
    if not import_source.is_dir():
        if args.json:
            print(json.dumps({"skill": args.name, "updated": False, "error": f"cached source not found: {import_source}"}, indent=2))
        else:
            print(f"cached source not found: {import_source}")
        return 1

    result = import_skill_directory(
        source=import_source,
        destination_root=paths.skills,
        skill_name=args.name,
        overwrite=True,
    )
    record["imported_at"] = _utc_now()
    write_source_records(source_state_path, upsert_source_record(records, record))
    write_registry(paths.skills, paths.state / "registry.yaml")
    if args.json:
        print(
            json.dumps(
                {
                    "skill": result.skill,
                    "source": str(result.source),
                    "target": str(result.target),
                    "replaced": result.replaced,
                },
                indent=2,
            )
        )
        return 0
    print(f"updated: {result.skill}")
    print(f"source: {result.source}")
    print(f"target: {result.target}")
    print("rebuilt: registry")
    return 0


def _cmd_skill_source_list(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    records = load_source_records(paths.state / "skill-sources.json")
    if args.json:
        print(json.dumps({"records": records}, indent=2))
        return 0
    for record in records:
        print(record.get("skill", ""))
    return 0


def _cmd_skill_source_show(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    records = load_source_records(paths.state / "skill-sources.json")
    record = find_source_record(records, args.name)
    if record is None:
        if args.json:
            print(json.dumps({"record": None}, indent=2))
        else:
            print(f"missing: {args.name}")
        return 1
    if args.json:
        print(json.dumps({"record": record}, indent=2))
        return 0
    for key, value in record.items():
        print(f"{key}: {value}")
    return 0


def _cmd_profile_list(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    for path in list_profiles(paths.profiles):
        print(path.stem)
    return 0


def _cmd_profile_show(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    profile = load_profile(paths.profiles / f"{args.name}.yaml")
    print(f"name: {profile.name}")
    print(f"agent: {profile.agent}")
    print(f"skills: [{', '.join(profile.skills)}]")
    print(f"exclude: [{', '.join(profile.exclude)}]")
    print(f"effective_skills: [{', '.join(profile.effective_skills())}]")
    return 0


def _cmd_profile_add(args: argparse.Namespace) -> int:
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


def _cmd_profile_remove(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    removed = remove_profile(paths.profiles, args.name)
    if removed:
        print(f"removed: {paths.profiles / f'{args.name}.yaml'}")
        return 0
    print(f"missing: {paths.profiles / f'{args.name}.yaml'}")
    return 1


def _cmd_profile_update(args: argparse.Namespace) -> int:
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


def _cmd_profile_clone(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    try:
        path = clone_profile(paths.profiles, args.name, args.to)
    except FileExistsError as error:
        print(f"exists: {error.args[0]}")
        return 1
    print(f"cloned: {path}")
    return 0


def _cmd_profile_rename(args: argparse.Namespace) -> int:
    paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
    try:
        path = rename_profile(paths.profiles, args.name, args.to)
    except FileExistsError as error:
        print(f"exists: {error.args[0]}")
        return 1
    print(f"renamed: {path}")
    return 0


def _cmd_profile_validate(args: argparse.Namespace) -> int:
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


_DISPATCH: dict[tuple[str, str | None], callable] = {
    ("agent", "detect"): _cmd_agent_detect,
    ("scan", None): _cmd_scan,
    ("ls", None): _cmd_ls,
    ("find", None): _cmd_find,
    ("audit", None): _cmd_audit,
    ("init", None): _cmd_init,
    ("registry", "build"): _cmd_registry_build,
    ("registry", "doctor"): _cmd_registry_doctor,
    ("sync", None): _cmd_sync,
    ("doctor", None): _cmd_doctor,
    ("install-state", "show"): _cmd_install_state_show,
    ("install-state", "record"): _cmd_install_state_record,
    ("skill", "import"): _cmd_skill_import,
    ("skill", "remove"): _cmd_skill_remove,
    ("skill", "update"): _cmd_skill_update,
    ("skill", "source"): None,
    ("profile", "list"): _cmd_profile_list,
    ("profile", "show"): _cmd_profile_show,
    ("profile", "add"): _cmd_profile_add,
    ("profile", "remove"): _cmd_profile_remove,
    ("profile", "update"): _cmd_profile_update,
    ("profile", "clone"): _cmd_profile_clone,
    ("profile", "rename"): _cmd_profile_rename,
    ("profile", "validate"): _cmd_profile_validate,
}

_SOURCE_DISPATCH: dict[str, callable] = {
    "list": _cmd_skill_source_list,
    "show": _cmd_skill_source_show,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"skill-hub {__version__}")
        return 0

    if args.command is None:
        parser.print_help()
        return 0

    subcommand = getattr(args, f"{args.command.replace('-', '_')}_command", None)

    if args.command == "skill" and subcommand == "source":
        source_sub = getattr(args, "skill_source_command", None)
        handler = _SOURCE_DISPATCH.get(source_sub)
        if handler is not None:
            return handler(args)
        parser.print_help()
        return 0

    handler = _DISPATCH.get((args.command, subcommand))
    if handler is not None:
        return handler(args)

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
