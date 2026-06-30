from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from skill_hub_manager.installer_bootstrap import run_install_flow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--checkout-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--update-manager", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_install_flow(
        repo_url=args.repo_url,
        checkout_dir=Path(args.checkout_dir).expanduser(),
        workspace_root=Path(args.workspace_root).expanduser(),
        profile=args.profile,
        agent=args.agent,
        target_dir=Path(args.target_dir).expanduser(),
        skills=args.skill,
        update_manager=args.update_manager,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
