#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_REPO_URL = "https://github.com/cnyup/skill-hub-manager.git"
DEFAULT_CHECKOUT_DIR = Path.home() / "skill-hub-manager"
DEFAULT_WORKSPACE_ROOT = Path.home() / ".skill-hub"

MIN_PYTHON = (3, 11)


def preflight_checks() -> None:
    """Fail fast with a clear message if the environment is not ready."""
    if sys.version_info < MIN_PYTHON:
        raise SystemExit(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, "
            f"got {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}. "
            f"Install a newer Python from https://www.python.org/downloads/"
        )
    if not shutil.which("git"):
        raise SystemExit(
            "git not found on PATH. Install git first:\n"
            "  macOS:  xcode-select --install\n"
            "  Ubuntu: sudo apt install git\n"
            "  Fedora: sudo dnf install git"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clone or update skill-hub-manager, then initialize its local workspace."
    )
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--checkout-dir", default=str(DEFAULT_CHECKOUT_DIR))
    parser.add_argument("--workspace-root", default=str(DEFAULT_WORKSPACE_ROOT))
    parser.add_argument("--update-manager", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def current_origin(checkout_dir: Path) -> str | None:
    if not (checkout_dir / ".git").exists():
        return None
    result = run_capture(["git", "-C", str(checkout_dir), "remote", "get-url", "origin"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_revision(checkout_dir: Path) -> str:
    result = run_capture(["git", "-C", str(checkout_dir), "rev-parse", "HEAD"])
    if result.returncode != 0:
        raise ValueError(f"failed to read manager revision from: {checkout_dir}")
    return result.stdout.strip()


def checkout_status(repo_url: str, checkout_dir: Path) -> tuple[str, str]:
    if not checkout_dir.exists():
        return "absent", "checkout does not exist yet"
    if not checkout_dir.is_dir():
        return "conflict", "checkout path exists but is not a directory"
    origin = current_origin(checkout_dir)
    if origin is None:
        return "invalid", "checkout exists but is not a usable git clone"
    if origin != repo_url:
        return "mismatch", f"checkout origin mismatch: {origin}"
    return "match", f"checkout origin matches: {origin}"


def ensure_checkout(repo_url: str, checkout_dir: Path, update: bool) -> Path:
    if checkout_dir.exists() and not checkout_dir.is_dir():
        raise ValueError(f"checkout path exists but is not a directory: {checkout_dir}")
    if not checkout_dir.exists():
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", repo_url, str(checkout_dir)])
    else:
        origin = current_origin(checkout_dir)
        if origin is None:
            raise ValueError(
                f"checkout exists but is not a usable git clone: {checkout_dir}"
            )
        if origin != repo_url:
            raise ValueError(
                f"checkout origin mismatch: expected {repo_url}, found {origin}"
            )
        if update:
            run(["git", "-C", str(checkout_dir), "pull", "--ff-only"])

    cli = checkout_dir / "bin" / "skill-hub"
    if not cli.is_file():
        raise ValueError(f"missing manager cli: {cli}")
    return checkout_dir


def print_plan(repo_url: str, checkout_dir: Path, workspace_root: Path, update_manager: bool) -> None:
    status, status_reason = checkout_status(repo_url, checkout_dir)
    print("repo_url:", repo_url)
    print("checkout_dir:", checkout_dir)
    print("checkout_status:", status)
    print("checkout_status_reason:", status_reason)
    print("workspace_root:", workspace_root)
    print("update_manager:", "yes" if update_manager else "no")


def install_manager(
    repo_url: str,
    checkout_dir: Path,
    workspace_root: Path,
    update_manager: bool,
) -> None:
    checkout = ensure_checkout(repo_url=repo_url, checkout_dir=checkout_dir, update=update_manager)
    cli = checkout / "bin" / "skill-hub"

    run([str(cli), "init", "--root", str(workspace_root)])
    run([str(cli), "registry", "build", "--root", str(workspace_root)])
    run([str(cli), "doctor", "--root", str(workspace_root)])
    print("manager_revision:", current_revision(checkout))
    print("next_check:")
    print(f"  {cli} --version")
    print(f"  {cli} registry doctor --root {workspace_root}")


def main(argv: list[str] | None = None) -> int:
    preflight_checks()
    args = build_parser().parse_args(argv)
    checkout_dir = Path(args.checkout_dir).expanduser()
    workspace_root = Path(args.workspace_root).expanduser()

    print_plan(
        repo_url=args.repo_url,
        checkout_dir=checkout_dir,
        workspace_root=workspace_root,
        update_manager=args.update_manager,
    )
    if args.plan_only:
        return 0

    install_manager(
        repo_url=args.repo_url,
        checkout_dir=checkout_dir,
        workspace_root=workspace_root,
        update_manager=args.update_manager,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
