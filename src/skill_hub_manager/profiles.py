from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    name: str
    agent: str
    skills: list[str]
    exclude: list[str] = field(default_factory=list)

    def effective_skills(self) -> list[str]:
        excluded = set(self.exclude)
        return [skill for skill in self.skills if skill not in excluded]


def load_profile(path: Path) -> Profile:
    data = _parse_simple_profile_yaml(path.read_text(encoding="utf-8"))
    return Profile(
        name=data["name"],
        agent=data["agent"],
        skills=data.get("skills", []),
        exclude=data.get("exclude", []),
    )


def _parse_simple_profile_yaml(content: str) -> dict[str, str | list[str]]:
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
            raise ValueError(f"invalid profile line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value
        else:
            data[key] = []
            active_list = key
    return data
