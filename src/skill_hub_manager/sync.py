import json
from dataclasses import dataclass
from pathlib import Path

from skill_hub_manager.profiles import Profile
from skill_hub_manager.skills import Skill


@dataclass(frozen=True)
class SyncResult:
    linked: list[str]
    missing: list[str]
    removed: list[str]


def sync_profile(profile: Profile, skills: dict[str, Skill], target: Path, dry_run: bool = False) -> SyncResult:
    target.mkdir(parents=True, exist_ok=True)
    linked: list[str] = []
    missing: list[str] = []
    removed: list[str] = []
    desired_skills = profile.effective_skills()
    desired = set(desired_skills)
    for child in sorted(target.iterdir()):
        if child.name in desired:
            continue
        if child.is_symlink():
            removed.append(child.name)
            if not dry_run:
                child.unlink()
    for skill_name in desired_skills:
        skill = skills.get(skill_name)
        if skill is None:
            missing.append(skill_name)
            continue
        link = target / skill_name
        linked.append(skill_name)
        if dry_run:
            continue
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(skill.path, target_is_directory=True)
    return SyncResult(linked=linked, missing=missing, removed=removed)


def write_sync_state(
    state_file: Path,
    profile: Profile,
    target: Path,
    linked: list[str],
    missing: list[str],
    removed: list[str],
) -> Path:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "profile": profile.name,
        "agent": profile.agent,
        "target": str(target),
        "linked": linked,
        "missing": missing,
        "removed": removed,
    }
    state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state_file


def render_sync_result_json(
    profile: Profile,
    target: Path,
    linked: list[str],
    missing: list[str],
    removed: list[str],
    dry_run: bool,
) -> str:
    payload = {
        "mode": "dry-run" if dry_run else "apply",
        "profile": profile.name,
        "agent": profile.agent,
        "target": str(target),
        "linked": linked,
        "missing": missing,
        "removed": removed,
    }
    return json.dumps(payload, indent=2)
