import json
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


def load_registry_entries(registry_file: Path) -> list[dict[str, str | list[str]]]:
    if not registry_file.exists():
        return []

    entries: list[dict[str, str | list[str]]] = []
    current: dict[str, str | list[str]] | None = None
    for raw_line in registry_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line == "skills:" or not line.strip():
            continue
        if line.startswith("  ") and not line.startswith("    "):
            current = {"name": line.strip().removesuffix(":")}
            entries.append(current)
            continue
        if current is None or not line.startswith("    "):
            continue
        key, value = line.strip().split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            current[key] = [] if not inner else [item.strip() for item in inner.split(",")]
            continue
        current[key] = value
    return entries


def find_registry_entries(
    entries: list[dict[str, str | list[str]]],
    query: str,
) -> list[dict[str, str | list[str]]]:
    needle = query.casefold()
    matches: list[dict[str, str | list[str]]] = []
    for entry in entries:
        haystacks: list[str] = []
        for key in ("name", "description", "path", "visibility"):
            value = entry.get(key, "")
            if isinstance(value, str):
                haystacks.append(value)
        for key in ("agents", "tags"):
            value = entry.get(key, [])
            if isinstance(value, list):
                haystacks.extend(str(item) for item in value)
        if any(needle in haystack.casefold() for haystack in haystacks):
            matches.append(entry)
    return matches


def doctor_registry(vault: Path, registry_file: Path) -> list[str]:
    scanned = scan_skills(vault)
    registry_entries = load_registry_entries(registry_file)
    registry_by_name = {str(entry["name"]): entry for entry in registry_entries}
    issues: list[str] = []

    scanned_names = set(scanned)
    registry_names = set(registry_by_name)

    for name in sorted(scanned_names & registry_names):
        registry_path = registry_by_name[name].get("path")
        vault_path = str(scanned[name].path)
        if isinstance(registry_path, str) and registry_path != vault_path:
            issues.append(f"path-mismatch: {name} registry={registry_path} vault={vault_path}")

    for name in sorted(registry_by_name):
        if name not in scanned_names:
            issues.append(f"stale-registry-skill: {name}")

    for name in sorted(scanned):
        if name not in registry_names:
            issues.append(f"unregistered-skill: {name}")

    return issues


def render_registry_doctor_json(issues: list[str]) -> str:
    return json.dumps({"ok": not issues, "issues": issues}, indent=2)
