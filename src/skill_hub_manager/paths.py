from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    skills: Path
    profiles: Path
    state: Path


def workspace_paths(root: Path) -> WorkspacePaths:
    return WorkspacePaths(
        root=root,
        skills=root / "skills",
        profiles=root / "profiles",
        state=root / "state",
    )


def initialize_workspace(root: Path) -> WorkspacePaths:
    paths = workspace_paths(root)
    paths.skills.mkdir(parents=True, exist_ok=True)
    paths.profiles.mkdir(parents=True, exist_ok=True)
    paths.state.mkdir(parents=True, exist_ok=True)

    default_profile = paths.profiles / "default.yaml"
    if not default_profile.exists():
        default_profile.write_text(
            "name: default\nagent: codex\nskills:\n",
            encoding="utf-8",
        )

    return paths
