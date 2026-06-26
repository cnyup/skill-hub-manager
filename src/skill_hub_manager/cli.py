import argparse
from pathlib import Path

from skill_hub_manager import __version__
from skill_hub_manager.audit import audit_profiles
from skill_hub_manager.doctor import find_broken_links, find_missing_expected_links, load_sync_target
from skill_hub_manager.paths import initialize_workspace, resolve_workspace_root, workspace_paths
from skill_hub_manager.profiles import list_profiles, load_profile
from skill_hub_manager.registry import find_registry_entries, load_registry_entries, write_registry
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

    sync = subparsers.add_parser("sync")
    sync.add_argument("--vault")
    sync.add_argument("--profile")
    sync.add_argument("--root")
    sync.add_argument("--target", required=True)

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
    if args.command == "sync":
        vault, profile_path = _resolve_sync_paths(args)
        profile = load_profile(profile_path)
        target = Path(args.target)
        result = sync_profile(profile, scan_skills(vault), target)
        if args.root:
            paths = workspace_paths(resolve_workspace_root(_optional_path(args.root)))
            write_sync_state(
                paths.state / "last-sync.json",
                profile,
                target,
                result.linked,
                result.missing,
                result.removed,
            )
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
