import argparse
from pathlib import Path

from skill_hub_manager import __version__
from skill_hub_manager.audit import audit_profiles
from skill_hub_manager.doctor import find_broken_links, find_missing_expected_links, load_sync_target
from skill_hub_manager.paths import initialize_workspace, resolve_workspace_root, workspace_paths
from skill_hub_manager.profiles import (
    Profile,
    clone_profile,
    list_profiles,
    load_profile,
    remove_profile,
    rename_profile,
    update_profile,
    validate_profile,
    write_profile,
)
from skill_hub_manager.registry import doctor_registry, find_registry_entries, load_registry_entries, write_registry
from skill_hub_manager.skills import scan_skills
from skill_hub_manager.sync import sync_profile, write_sync_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-hub")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan")
    scan.add_argument("--vault")
    scan.add_argument("--root")

    ls_cmd = subparsers.add_parser("ls")
    ls_cmd.add_argument("--root", required=True)

    find_cmd = subparsers.add_parser("find")
    find_cmd.add_argument("--root", required=True)
    find_cmd.add_argument("--query", required=True)

    audit_cmd = subparsers.add_parser("audit")
    audit_cmd.add_argument("--root", required=True)

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

    sync = subparsers.add_parser("sync")
    sync.add_argument("--vault")
    sync.add_argument("--profile")
    sync.add_argument("--root")
    sync.add_argument("--target", required=True)
    sync.add_argument("--dry-run", action="store_true")

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--target")
    doctor.add_argument("--root")

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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"skill-hub {__version__}")
        return 0
    if args.command == "scan":
        for name in scan_skills(_resolve_scan_vault(args)):
            print(name)
        return 0
    if args.command == "ls":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        for entry in load_registry_entries(paths.state / "registry.yaml"):
            print(entry["name"])
        return 0
    if args.command == "find":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        entries = load_registry_entries(paths.state / "registry.yaml")
        for entry in find_registry_entries(entries, args.query):
            print(entry["name"])
        return 0
    if args.command == "audit":
        paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
        for report in audit_profiles(paths.profiles, paths.skills):
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
        for profile_path in profile_paths:
            profile = load_profile(profile_path)
            issues = validate_profile(profile, available_skills)
            if issues:
                has_issues = True
                print(f"profile: {profile.name}")
                for issue in issues:
                    print(issue)
                continue
            print(f"ok: {profile.name}")
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


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
