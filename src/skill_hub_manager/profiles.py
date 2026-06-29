from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    name: str
    agent: str
    skills: list[str]
    exclude: list[str] = field(default_factory=list)

    def effective_skills(self) -> list[str]:
        return [
            skill
            for skill in self.skills
            if not any(fnmatch(skill, pattern) for pattern in self.exclude)
        ]


def load_profile(path: Path) -> Profile:
    data = _parse_simple_profile_yaml(path.read_text(encoding="utf-8"))
    return Profile(
        name=data["name"],
        agent=data["agent"],
        skills=data.get("skills", []),
        exclude=data.get("exclude", []),
    )


def list_profiles(profiles_dir: Path) -> list[Path]:
    if not profiles_dir.exists():
        return []
    return sorted(path for path in profiles_dir.iterdir() if path.is_file() and path.suffix == ".yaml")


def write_profile(profiles_dir: Path, profile: Profile) -> Path:
    profiles_dir.mkdir(parents=True, exist_ok=True)
    path = profile_path(profiles_dir, profile.name)
    path.write_text(_render_profile(profile), encoding="utf-8")
    return path


def remove_profile(profiles_dir: Path, name: str) -> bool:
    path = profile_path(profiles_dir, name)
    if not path.exists():
        return False
    path.unlink()
    return True


def profile_path(profiles_dir: Path, name: str) -> Path:
    return profiles_dir / f"{name}.yaml"


def update_profile(
    profile: Profile,
    agent: str | None = None,
    add_skills: list[str] | None = None,
    remove_skills: list[str] | None = None,
    add_exclude: list[str] | None = None,
    remove_exclude: list[str] | None = None,
) -> Profile:
    return Profile(
        name=profile.name,
        agent=agent or profile.agent,
        skills=_merge_list(profile.skills, add_skills or [], remove_skills or []),
        exclude=_merge_list(profile.exclude, add_exclude or [], remove_exclude or []),
    )


def clone_profile(profiles_dir: Path, source_name: str, target_name: str) -> Path:
    profile = load_profile(profile_path(profiles_dir, source_name))
    return write_profile(
        profiles_dir,
        Profile(
            name=target_name,
            agent=profile.agent,
            skills=profile.skills,
            exclude=profile.exclude,
        ),
    )


def rename_profile(profiles_dir: Path, source_name: str, target_name: str) -> Path:
    clone_path = clone_profile(profiles_dir, source_name, target_name)
    remove_profile(profiles_dir, source_name)
    return clone_path


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


def _render_profile(profile: Profile) -> str:
    lines = [
        f"name: {profile.name}",
        f"agent: {profile.agent}",
        "skills:",
    ]
    lines.extend(f"  - {skill}" for skill in profile.skills)
    if profile.exclude:
        lines.append("exclude:")
        lines.extend(f"  - {pattern}" for pattern in profile.exclude)
    return "\n".join(lines) + "\n"


def _merge_list(existing: list[str], additions: list[str], removals: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    removal_set = set(removals)
    for item in existing:
        if item in removal_set or item in seen:
            continue
        result.append(item)
        seen.add(item)
    for item in additions:
        if item in removal_set or item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result
