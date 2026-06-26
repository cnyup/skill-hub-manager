from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path


def scan_skills(vault: Path) -> dict[str, Skill]:
    found: dict[str, Skill] = {}
    if not vault.exists():
        return found
    for child in sorted(vault.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            found[child.name] = Skill(name=child.name, path=child)
    return found
