from dataclasses import dataclass
from pathlib import Path

from skill_hub_manager.profiles import Profile
from skill_hub_manager.skills import Skill


@dataclass(frozen=True)
class SyncResult:
    linked: list[str]
    missing: list[str]


def sync_profile(profile: Profile, skills: dict[str, Skill], target: Path) -> SyncResult:
    target.mkdir(parents=True, exist_ok=True)
    linked: list[str] = []
    missing: list[str] = []
    for skill_name in profile.skills:
        skill = skills.get(skill_name)
        if skill is None:
            missing.append(skill_name)
            continue
        link = target / skill_name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(skill.path, target_is_directory=True)
        linked.append(skill_name)
    return SyncResult(linked=linked, missing=missing)
