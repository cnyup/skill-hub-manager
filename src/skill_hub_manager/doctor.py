from pathlib import Path


def find_broken_links(target: Path) -> list[str]:
    if not target.exists():
        return []
    broken: list[str] = []
    for child in sorted(target.iterdir()):
        if child.is_symlink() and not child.exists():
            broken.append(child.name)
    return broken
