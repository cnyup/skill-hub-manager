import argparse
from pathlib import Path

from skill_hub_manager import __version__
from skill_hub_manager.doctor import find_broken_links
from skill_hub_manager.profiles import load_profile
from skill_hub_manager.skills import scan_skills
from skill_hub_manager.sync import sync_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill-hub")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan")
    scan.add_argument("--vault", required=True)

    sync = subparsers.add_parser("sync")
    sync.add_argument("--vault", required=True)
    sync.add_argument("--profile", required=True)
    sync.add_argument("--target", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--target", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"skill-hub {__version__}")
        return 0
    if args.command == "scan":
        for name in scan_skills(Path(args.vault)):
            print(name)
        return 0
    if args.command == "sync":
        profile = load_profile(Path(args.profile))
        result = sync_profile(profile, scan_skills(Path(args.vault)), Path(args.target))
        for name in result.linked:
            print(f"linked: {name}")
        for name in result.missing:
            print(f"missing: {name}")
        return 1 if result.missing else 0
    if args.command == "doctor":
        broken = find_broken_links(Path(args.target))
        for name in broken:
            print(f"broken: {name}")
        return 1 if broken else 0
    parser.print_help()
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
