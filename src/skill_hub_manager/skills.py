from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    description: str = ""
    visibility: str = "private"
    agents: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


def scan_skills(vault: Path) -> dict[str, Skill]:
    found: dict[str, Skill] = {}
    if not vault.exists():
        return found
    for child in sorted(vault.iterdir()):
        skill_file = child / "SKILL.md"
        if child.is_dir() and skill_file.is_file():
            found[child.name] = _load_skill(child.name, skill_file)
    return found


def _load_skill(directory_name: str, skill_file: Path) -> Skill:
    metadata = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    return Skill(
        name=str(metadata.get("name", directory_name)),
        path=skill_file.parent,
        description=str(metadata.get("description", "")),
        visibility=str(metadata.get("visibility", "private")),
        agents=tuple(str(agent) for agent in metadata.get("agents", [])),
        tags=tuple(str(tag) for tag in metadata.get("tags", [])),
    )


def _parse_frontmatter(content: str) -> dict[str, str | list[str]]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        frontmatter.append(line)
    else:
        return {}

    return _parse_simple_yaml("\n".join(frontmatter))


def _parse_simple_yaml(content: str) -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = {}
    active_list: str | None = None
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - "):
            if active_list is None:
                raise ValueError("list item found before list key")
            value = line.removeprefix("  - ").strip()
            items = data.setdefault(active_list, [])
            if not isinstance(items, list):
                raise ValueError(f"{active_list} is not a list")
            items.append(value)
            continue
        active_list = None
        if ":" not in line:
            raise ValueError(f"invalid metadata line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value
        else:
            data[key] = []
            active_list = key
    return data
