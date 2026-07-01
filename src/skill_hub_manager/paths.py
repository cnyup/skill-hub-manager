from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    skills: Path
    sources: Path
    profiles: Path
    state: Path


def default_workspace_root() -> Path:
    return Path.home() / ".skill-hub"


def workspace_paths(root: Path) -> WorkspacePaths:
    return WorkspacePaths(
        root=root,
        skills=root / "skills",
        sources=root / "sources",
        profiles=root / "profiles",
        state=root / "state",
    )


def install_state_file(root: Path) -> Path:
    return workspace_paths(root).state / "install-targets.json"


def initialize_workspace(root: Path) -> WorkspacePaths:
    paths = workspace_paths(root)
    paths.skills.mkdir(parents=True, exist_ok=True)
    paths.sources.mkdir(parents=True, exist_ok=True)
    paths.profiles.mkdir(parents=True, exist_ok=True)
    paths.state.mkdir(parents=True, exist_ok=True)

    default_profile = paths.profiles / "default.yaml"
    if not default_profile.exists():
        default_profile.write_text(
            "name: default\nagent: codex\nskills:\n",
            encoding="utf-8",
        )

    return paths


def resolve_workspace_root(root: Path | None) -> Path:
    return root if root is not None else default_workspace_root()
