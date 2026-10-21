#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


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


@dataclass(frozen=True)
class ResolvedSource:
    mode: str
    import_source: Path
    repo_url: str | None
    checkout_root: Path | None = None
    git_ref: str | None = None
    import_subpath: str | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install a business skill into an existing skill-hub-manager workspace."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--workspace-root", default=str(DEFAULT_WORKSPACE_ROOT))
    parser.add_argument("--manager-cli")
    parser.add_argument("--name")
    parser.add_argument("--git-ref")
    parser.add_argument("--source-subpath")
    parser.add_argument("--profile")
    parser.add_argument("--target-dir")
    parser.add_argument("--agent")
    parser.add_argument("--update-source", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def slugify_repo(repo_url: str) -> str:
    cleaned = repo_url.removesuffix(".git")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned)


def normalize_subpath(subpath: str) -> str:
    cleaned = subpath.strip().strip("/")
    parts = cleaned.split("/")
    if not cleaned or any(part in {"", ".", ".."} for part in parts) or "\\" in cleaned:
        raise ValueError("source subpath cannot be empty")
    return cleaned


def normalize_repo_identity(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.scheme == "file":
        return str(Path(parsed.path).resolve()).removesuffix(".git")
    if parsed.scheme in {"http", "https", "ssh"} and parsed.netloc:
        host = parsed.netloc.lower()
        if "@" in host:
            host = host.split("@", 1)[1]
        return f"{host}/{parsed.path.strip('/').removesuffix('.git').lower()}"
    if repo_url.startswith("git@") and ":" in repo_url:
        host, path = repo_url.split(":", 1)
        return f"{host.split('@', 1)[1].lower()}/{path.strip('/').removesuffix('.git').lower()}"
    return repo_url.removesuffix(".git")


def parse_source(
    source: str,
    workspace_root: Path,
    name: str | None,
    git_ref: str | None = None,
    source_subpath: str | None = None,
) -> ResolvedSource:
    maybe_local = Path(source).expanduser()
    if maybe_local.exists():
        import_source = maybe_local.resolve()
        if source_subpath:
            source_subpath = normalize_subpath(source_subpath)
            import_source = import_source / source_subpath
        return ResolvedSource(
            mode="local",
            import_source=import_source,
            repo_url=None,
            import_subpath=source_subpath,
        )

    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 5 and parts[2] == "tree":
            owner, repo = parts[:2]
            tree_tail = parts[3:]
            branch = git_ref or tree_tail[0]
            if source_subpath:
                subpath = normalize_subpath(source_subpath)
            elif git_ref:
                ref_parts = [part for part in git_ref.split("/") if part]
                if tree_tail[: len(ref_parts)] != ref_parts:
                    raise ValueError(
                        "GitHub tree URL does not match --git-ref; pass a matching ref or explicit --source-subpath"
                    )
                subpath = normalize_subpath("/".join(tree_tail[len(ref_parts) :]))
            else:
                subpath = normalize_subpath("/".join(tree_tail[1:]))
            repo_url = f"https://github.com/{owner}/{repo}.git"
            cache_dir = workspace_root / "sources" / slugify_repo(f"{owner}/{repo}@{branch}")
            return ResolvedSource(
                mode="github-tree",
                import_source=cache_dir / subpath,
                repo_url=repo_url,
                checkout_root=cache_dir,
                git_ref=branch,
                import_subpath=subpath,
            )
        if len(parts) >= 2:
            owner, repo = parts[:2]
            repo_url = f"https://github.com/{owner}/{repo.removesuffix('.git')}.git"
            ref = git_ref
            cache_suffix = f"{owner}/{repo}" if ref is None else f"{owner}/{repo}@{ref}"
            cache_dir = workspace_root / "sources" / slugify_repo(cache_suffix)
            if source_subpath:
                source_subpath = normalize_subpath(source_subpath)
                import_source = cache_dir / source_subpath
            elif name:
                import_source = cache_dir / "skills" / name
            else:
                import_source = cache_dir
            return ResolvedSource(
                mode="github-repo",
                import_source=import_source,
                repo_url=repo_url,
                checkout_root=cache_dir,
                git_ref=ref,
                import_subpath=source_subpath,
            )

    if parsed.scheme == "file" or source.endswith(".git"):
        cache_suffix = source if git_ref is None else f"{source}@{git_ref}"
        cache_dir = workspace_root / "sources" / slugify_repo(cache_suffix)
        if source_subpath:
            source_subpath = normalize_subpath(source_subpath)
            import_source = cache_dir / source_subpath
        elif name:
            import_source = cache_dir / "skills" / name
        else:
            import_source = cache_dir
        return ResolvedSource(
            mode="git-repo",
            import_source=import_source,
            repo_url=source,
            checkout_root=cache_dir,
            git_ref=git_ref,
            import_subpath=source_subpath,
        )

    raise ValueError(f"unsupported source: {source}")


def run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def current_origin(checkout_dir: Path) -> str | None:
    if not (checkout_dir / ".git").exists():
        return None
    result = run_capture(["git", "-C", str(checkout_dir), "remote", "get-url", "origin"])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def ensure_remote_checkout(repo_url: str, checkout_dir: Path, update: bool, git_ref: str | None = None) -> Path:
    if not checkout_dir.exists():
        checkout_dir.parent.mkdir(parents=True, exist_ok=True)
        command = ["git", "clone"]
        if git_ref:
            command.extend(["--branch", git_ref, "--single-branch"])
        command.extend([repo_url, str(checkout_dir)])
        run(command)
        return checkout_dir
    if not checkout_dir.is_dir():
        raise ValueError(f"remote cache path exists but is not a directory: {checkout_dir}")
    origin = current_origin(checkout_dir)
    if origin is None:
        raise ValueError(f"remote cache is not a usable git checkout: {checkout_dir}")
    if normalize_repo_identity(origin) != normalize_repo_identity(repo_url):
        raise ValueError(f"remote cache origin mismatch: expected {repo_url}, found {origin}")
    if git_ref:
        run(["git", "-C", str(checkout_dir), "fetch", "origin", git_ref])
        run(["git", "-C", str(checkout_dir), "checkout", "--detach", "FETCH_HEAD"])
    if update and git_ref:
        return checkout_dir
    if update:
        run(["git", "-C", str(checkout_dir), "pull", "--ff-only"])
    return checkout_dir


def print_plan(
    mode: str,
    source: str,
    workspace_root: Path,
    resolved_source: Path,
    repo_url: str | None,
    checkout_root: Path | None,
    git_ref: str | None,
    profile: str | None,
    target_dir: str | None,
    update_source: bool,
) -> None:
    print("mode:", mode)
    print("source:", source)
    if repo_url:
        print("repo_url:", repo_url)
        print("cache_checkout:", checkout_root or (resolved_source if resolved_source.is_dir() else resolved_source.parent))
    if git_ref:
        print("git_ref:", git_ref)
    if resolved_source:
        parent = checkout_root if checkout_root is not None else resolved_source.parent
        if checkout_root is not None and resolved_source != checkout_root:
            try:
                print("import_subpath:", resolved_source.relative_to(parent))
            except ValueError:
                pass
    print("workspace_root:", workspace_root)
    print("import_source:", resolved_source)
    if checkout_root is not None and resolved_source == checkout_root:
        print("import_resolution:", "deferred-until-checkout")
    print("update_source:", "yes" if update_source else "no")
    print("profile:", profile or "")
    print("target_dir:", target_dir or "")


def cli_command(override: str | None) -> list[str]:
    if override:
        return [str(Path(override).expanduser())]
    env_value = os.environ.get("SKILL_HUB_CMD")
    if env_value:
        return [env_value]
    wrapper = Path.home() / "skill-hub-manager" / "bin" / "skill-hub"
    if wrapper.is_file():
        return [str(wrapper)]
    installed = shutil.which("skill-hub")
    if installed:
        return [installed]
    raise ValueError("skill-hub command not found; install skill-hub-manager first")


def detect_single_skill_root(checkout_root: Path) -> Path:
    if (checkout_root / "SKILL.md").is_file():
        return checkout_root
    skills_root = checkout_root / "skills"
    if not skills_root.is_dir():
        raise ValueError(
            "repository source requires --name or a GitHub tree URL pointing to a specific skill"
        )
    candidates = [path for path in skills_root.iterdir() if (path / "SKILL.md").is_file()]
    if len(candidates) != 1:
        raise ValueError(
            "repository source resolves to multiple skills; pass --name or use a GitHub tree URL"
        )
    return candidates[0]


def determine_import_source(resolved: ResolvedSource) -> Path:
    if resolved.checkout_root is None:
        return resolved.import_source
    if resolved.import_source != resolved.checkout_root:
        if not resolved.import_source.exists():
            raise ValueError(f"resolved import source does not exist: {resolved.import_source}")
        return resolved.import_source
    return detect_single_skill_root(resolved.checkout_root)


def ensure_profile(manager_cli: list[str], workspace_root: Path, profile: str, agent: str | None, skill: str) -> None:
    profile_path = workspace_root / "profiles" / f"{profile}.yaml"
    if not profile_path.is_file():
        if not agent:
            raise ValueError(f"profile {profile} does not exist; pass --agent to create it")
        run([*manager_cli, "profile", "add", "--root", str(workspace_root), "--name", profile, "--agent", agent, "--skill", skill])
        return
    run([*manager_cli, "profile", "update", "--root", str(workspace_root), "--name", profile, "--add-skill", skill])


def main(argv: list[str] | None = None) -> int:
    preflight_checks()
    args = build_parser().parse_args(argv)
    workspace_root = Path(args.workspace_root).expanduser()
    resolved = parse_source(
        args.source,
        workspace_root,
        args.name,
        git_ref=args.git_ref,
        source_subpath=args.source_subpath,
    )
    import_source = resolved.import_source

    if args.target_dir and not args.profile:
        raise ValueError("--target-dir requires --profile")

    if args.plan_only:
        print_plan(
            mode=resolved.mode,
            source=args.source,
            workspace_root=workspace_root,
            resolved_source=import_source,
            repo_url=resolved.repo_url,
            checkout_root=resolved.checkout_root,
            git_ref=resolved.git_ref,
            profile=args.profile,
            target_dir=args.target_dir,
            update_source=args.update_source,
        )
        return 0

    if resolved.checkout_root is not None:
        ensure_remote_checkout(
            resolved.repo_url,
            resolved.checkout_root,
            args.update_source,
            git_ref=resolved.git_ref,
        )
        import_source = determine_import_source(resolved)

    print_plan(
        mode=resolved.mode,
        source=args.source,
        workspace_root=workspace_root,
        resolved_source=import_source,
        repo_url=resolved.repo_url,
        checkout_root=resolved.checkout_root,
        git_ref=resolved.git_ref,
        profile=args.profile,
        target_dir=args.target_dir,
        update_source=args.update_source,
    )
    manager_cli = cli_command(args.manager_cli)
    force_import = args.force or args.update_source
    run([*manager_cli, "init", "--root", str(workspace_root)])
    run(
        [
            *manager_cli,
            "skill",
            "import",
            "--root",
            str(workspace_root),
            "--source",
            str(import_source),
            *(["--name", args.name] if args.name else []),
            *(["--force"] if force_import else []),
            *(["--source-ref", args.source] if args.source else []),
            *(["--source-type", resolved.mode] if resolved.mode else []),
            *(["--repo-url", resolved.repo_url] if resolved.repo_url else []),
            *(["--git-ref", resolved.git_ref] if resolved.git_ref else []),
            *(["--cache-checkout", str(resolved.checkout_root)] if resolved.checkout_root else []),
            *(["--import-subpath", resolved.import_subpath] if resolved.import_subpath else []),
        ]
    )
    run([*manager_cli, "registry", "build", "--root", str(workspace_root)])

    imported_name = args.name or import_source.name
    if args.profile:
        ensure_profile(manager_cli, workspace_root, args.profile, args.agent, imported_name)
    if args.target_dir:
        sync_command = [
            *manager_cli,
            "sync",
            "--root",
            str(workspace_root),
            "--target",
            args.target_dir,
        ]
        if args.profile:
            sync_command.extend(["--profile", str(workspace_root / "profiles" / f"{args.profile}.yaml")])
        run(sync_command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
