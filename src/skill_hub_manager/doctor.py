import json
from pathlib import Path


def find_broken_links(target: Path) -> list[str]:
    if not target.exists():
        return []
    broken: list[str] = []
    for child in sorted(target.iterdir()):
        if child.is_symlink() and not child.exists():
            broken.append(child.name)
    return broken


def load_sync_target(state_file: Path) -> Path | None:
    if not state_file.exists():
        return None
    state = json.loads(state_file.read_text(encoding="utf-8"))
    target = state.get("target")
    return Path(target) if isinstance(target, str) and target else None


def find_missing_expected_links(target: Path, state_file: Path) -> list[str]:
    if not state_file.exists():
        return []
    state = json.loads(state_file.read_text(encoding="utf-8"))
    expected = sorted(str(name) for name in state.get("linked", []))
    missing: list[str] = []
    for name in expected:
        if not (target / name).exists() and not (target / name).is_symlink():
            missing.append(name)
    return missing
