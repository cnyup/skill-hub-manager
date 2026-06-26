from pathlib import Path

from skill_hub_manager.skills import scan_skills


def build_registry(vault: Path) -> str:
    lines = ["skills:"]
    for name, skill in scan_skills(vault).items():
        lines.append(f"  {name}:")
        lines.append(f"    path: {skill.path}")
        lines.append(f"    visibility: {skill.visibility}")
        if skill.description:
            lines.append(f"    description: {skill.description}")
        if skill.agents:
            lines.append(f"    agents: [{', '.join(skill.agents)}]")
        if skill.tags:
            lines.append(f"    tags: [{', '.join(skill.tags)}]")
    lines.append("")
    return "\n".join(lines)


def write_registry(vault: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_registry(vault), encoding="utf-8")
    return output
