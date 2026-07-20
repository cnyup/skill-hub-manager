import json
from dataclasses import dataclass
from pathlib import Path

from skill_hub_manager.profiles import Profile
from skill_hub_manager.skills import Skill
from skill_hub_manager.state_io import atomic_write_text
from skill_hub_manager.validation import validate_identifier


@dataclass(frozen=True)
class SyncResult:
    linked: list[str]
    missing: list[str]
    removed: list[str]
    conflicts: list[str]


def sync_profile(profile: Profile, skills: dict[str, Skill], target: Path, dry_run: bool = False) -> SyncResult:
    linked: list[str] = []
    missing: list[str] = []
    removed: list[str] = []
    conflicts: list[str] = []
    desired_skills = profile.effective_skills()
    for skill_name in desired_skills:
        validate_identifier(skill_name, "skill name")
    desired = set(desired_skills)
    vault_roots = {skill.path.parent.resolve() for skill in skills.values()}
    if target.exists():
        if not target.is_dir():
            raise ValueError(f"sync target is not a directory: {target}")
        for child in sorted(target.iterdir()):
            if child.name in desired or not child.is_symlink():
                continue
            if _is_managed_link(child, vault_roots):
                removed.append(child.name)
                if not dry_run:
                    child.unlink()
    elif not dry_run:
        target.mkdir(parents=True, exist_ok=True)
    for skill_name in desired_skills:
        skill = skills.get(skill_name)
        if skill is None:
            missing.append(skill_name)
            continue
        link = target / skill_name
        if dry_run:
            linked.append(skill_name)
            continue
        if link.exists() or link.is_symlink():
            if link.is_symlink() and _is_managed_link(link, vault_roots):
                link.unlink()
            elif link.is_symlink() and link.resolve() == skill.path.resolve():
                linked.append(skill_name)
                continue
            else:
                conflicts.append(skill_name)
                continue
        link.symlink_to(skill.path, target_is_directory=True)
        linked.append(skill_name)
    return SyncResult(linked=linked, missing=missing, removed=removed, conflicts=conflicts)


def _is_managed_link(link: Path, vault_roots: set[Path]) -> bool:
    if not link.is_symlink():
        return False
    try:
        resolved = link.resolve(strict=False)
    except OSError:
        return False
    return any(resolved.parent == vault_root for vault_root in vault_roots)


def write_sync_state(
    state_file: Path,
    profile: Profile,
    target: Path,
    linked: list[str],
    missing: list[str],
    removed: list[str],
    conflicts: list[str] | None = None,
) -> Path:
    state = {
        "profile": profile.name,
        "agent": profile.agent,
        "target": str(target),
        "linked": linked,
        "missing": missing,
        "removed": removed,
        "conflicts": conflicts or [],
    }
    return atomic_write_text(state_file, json.dumps(state, indent=2) + "\n")


def render_sync_result_json(
    profile: Profile,
    target: Path,
    linked: list[str],
    missing: list[str],
    removed: list[str],
    conflicts: list[str] | None = None,
    dry_run: bool = False,
) -> str:
    payload = {
        "mode": "dry-run" if dry_run else "apply",
        "profile": profile.name,
        "agent": profile.agent,
        "target": str(target),
        "linked": linked,
        "missing": missing,
        "removed": removed,
        "conflicts": conflicts or [],
    }
    return json.dumps(payload, indent=2)
