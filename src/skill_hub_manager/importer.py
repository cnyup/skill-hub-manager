from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportResult:
    skill: str
    source: Path
    target: Path
    replaced: bool


@dataclass(frozen=True)
class RemoveResult:
    skill: str
    target: Path
    removed: bool


def import_skill_directory(
    source: Path,
    destination_root: Path,
    skill_name: str | None = None,
    overwrite: bool = False,
) -> ImportResult:
    source_dir = source.expanduser().resolve()
    if not source_dir.is_dir():
        raise ValueError(f"skill source is not a directory: {source}")
    skill_file = source_dir / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"missing SKILL.md in source directory: {source_dir}")

    skill = skill_name or source_dir.name
    if not skill:
        raise ValueError("skill name cannot be empty")

    destination_root.mkdir(parents=True, exist_ok=True)
    target_dir = destination_root / skill
    replaced = target_dir.exists()
    if replaced and not overwrite:
        raise FileExistsError(target_dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    return ImportResult(skill=skill, source=source_dir, target=target_dir, replaced=replaced)


def remove_skill_directory(
    vault: Path,
    skill_name: str,
) -> RemoveResult:
    """Remove a skill directory from the vault.

    Returns RemoveResult with removed=False if the skill did not exist.
    Raises ValueError if the vault path is not a directory.
    """
    if not vault.is_dir():
        raise ValueError(f"vault is not a directory: {vault}")

    target_dir = vault / skill_name
    if not target_dir.exists():
        return RemoveResult(skill=skill_name, target=target_dir, removed=False)

    if not target_dir.is_dir():
        raise ValueError(f"skill path is not a directory: {target_dir}")

    shutil.rmtree(target_dir)
    return RemoveResult(skill=skill_name, target=target_dir, removed=True)
