from __future__ import annotations

import subprocess
from pathlib import Path


def _validate_checkout_dir(checkout_dir: Path) -> None:
    cli = checkout_dir / "bin" / "skill-hub"
    if not cli.is_file():
        raise ValueError(
            f"checkout directory does not look like a skill-hub-manager checkout: {checkout_dir}. "
            "Expected bin/skill-hub to exist. Choose a valid checkout_dir or remove the directory and retry."
        )


def ensure_manager_checkout(repo_url: str, checkout_dir: Path, update: bool) -> Path:
    if checkout_dir.exists() and not checkout_dir.is_dir():
        raise ValueError(
            f"checkout path exists but is not a directory: {checkout_dir}. "
            "Choose a different checkout_dir or remove the conflicting file."
        )

    if not checkout_dir.exists():
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", repo_url, str(checkout_dir)], check=True)
        _validate_checkout_dir(checkout_dir)
        return checkout_dir

    _validate_checkout_dir(checkout_dir)

    if update:
        subprocess.run(["git", "-C", str(checkout_dir), "pull", "--ff-only"], check=True)

    return checkout_dir


def run_install_flow(
    repo_url: str,
    checkout_dir: Path,
    workspace_root: Path,
    profile: str,
    agent: str,
    target_dir: Path,
    skills: list[str],
    update_manager: bool,
) -> None:
    checkout = ensure_manager_checkout(repo_url=repo_url, checkout_dir=checkout_dir, update=update_manager)
    cli = checkout / "bin" / "skill-hub"
    profile_path = workspace_root / "profiles" / f"{profile}.yaml"

    subprocess.run([str(cli), "init", "--root", str(workspace_root)], check=True)
    subprocess.run([str(cli), "registry", "build", "--root", str(workspace_root)], check=True)

    if not skills:
        raise ValueError("skills must be confirmed before validate/sync")

    profile_add = [
        str(cli),
        "profile",
        "add",
        "--root",
        str(workspace_root),
        "--name",
        profile,
        "--agent",
        agent,
    ]
    for skill in skills:
        profile_add.extend(["--skill", skill])
    subprocess.run(profile_add, check=True)
    subprocess.run([str(cli), "profile", "validate", "--root", str(workspace_root), "--name", profile], check=True)
    subprocess.run(
        [
            str(cli),
            "sync",
            "--root",
            str(workspace_root),
            "--profile",
            str(profile_path),
            "--target",
            str(target_dir),
        ],
        check=True,
    )
    subprocess.run([str(cli), "doctor", "--root", str(workspace_root)], check=True)
