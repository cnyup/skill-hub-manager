from dataclasses import dataclass, field
from fnmatch import fnmatch
import json
from pathlib import Path

from skill_hub_manager.state_io import atomic_write_text
from skill_hub_manager.validation import validate_identifier


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
    profile = Profile(
        name=data["name"],
        agent=data["agent"],
        skills=data.get("skills", []),
        exclude=data.get("exclude", []),
    )
    if profile.name != path.stem:
        raise ValueError(f"profile name does not match file name: {path}")
    validate_identifier(profile.name, "profile name")
    validate_identifier(profile.agent, "agent name")
    for skill in profile.skills:
        validate_identifier(skill, "skill name")
    return profile


def list_profiles(profiles_dir: Path) -> list[Path]:
    if not profiles_dir.exists():
        return []
    return sorted(path for path in profiles_dir.iterdir() if path.is_file() and path.suffix == ".yaml")


def write_profile(profiles_dir: Path, profile: Profile, overwrite: bool = False) -> Path:
    validate_identifier(profile.name, "profile name")
    validate_identifier(profile.agent, "agent name")
    for skill in profile.skills:
        validate_identifier(skill, "skill name")
    profiles_dir.mkdir(parents=True, exist_ok=True)
    path = profile_path(profiles_dir, profile.name)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    return atomic_write_text(path, _render_profile(profile))


def remove_profile(profiles_dir: Path, name: str) -> bool:
    path = profile_path(profiles_dir, name)
    if not path.exists():
        return False
    path.unlink()
    return True


def profile_path(profiles_dir: Path, name: str) -> Path:
    validate_identifier(name, "profile name")
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


def validate_profile(profile: Profile, available_skills: set[str] | None = None) -> list[str]:
    issues: list[str] = []
    if not profile.skills:
        issues.append("empty-skills")
    issues.extend(_duplicate_issues(profile.skills, "duplicate-skill"))
    if available_skills is not None:
        for skill in profile.skills:
            if skill not in available_skills:
                issues.append(f"missing-skill: {skill}")
    return _unique_preserving_order(issues)


def render_profile_validation_json(results: list[dict[str, str | bool | list[str]]]) -> str:
    return json.dumps({"profiles": results}, indent=2)


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


def _duplicate_issues(values: list[str], prefix: str) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen and value not in duplicates:
            issues.append(f"{prefix}: {value}")
            duplicates.add(value)
            continue
        seen.add(value)
    return issues


def _unique_preserving_order(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result
