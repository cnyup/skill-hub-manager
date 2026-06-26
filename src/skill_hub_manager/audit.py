from pathlib import Path

from skill_hub_manager.profiles import list_profiles, load_profile
from skill_hub_manager.skills import scan_skills


def audit_profiles(profiles_dir: Path, skills_dir: Path) -> list[dict[str, str | list[str]]]:
    available_skills = scan_skills(skills_dir)
    reports: list[dict[str, str | list[str]]] = []
    for profile_path in list_profiles(profiles_dir):
        profile = load_profile(profile_path)
        effective_skills = profile.effective_skills()
        missing_skills = [skill for skill in effective_skills if skill not in available_skills]
        reports.append(
            {
                "profile": profile.name,
                "agent": profile.agent,
                "effective_skills": effective_skills,
                "missing_skills": missing_skills,
            }
        )
    return reports
