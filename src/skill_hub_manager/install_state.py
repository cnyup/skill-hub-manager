from __future__ import annotations

import json
from pathlib import Path


def load_install_records(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    return [dict(record) for record in records]


def write_install_records(path: Path, records: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": records}, indent=2) + "\n", encoding="utf-8")
    return path


def find_install_record(records: list[dict[str, str]], agent: str) -> dict[str, str] | None:
    for record in records:
        if record.get("agent") == agent:
            return record
    return None


def upsert_install_record(
    records: list[dict[str, str]],
    record: dict[str, str],
) -> list[dict[str, str]]:
    updated: list[dict[str, str]] = []
    replaced = False
    for existing in records:
        if _same_install_target(existing, record):
            if not replaced:
                updated.append(dict(record))
                replaced = True
            continue
        updated.append(dict(existing))
    if not replaced:
        updated.append(dict(record))
    return updated


def _same_install_target(left: dict[str, str], right: dict[str, str]) -> bool:
    return left.get("agent") == right.get("agent") and left.get("profile") == right.get("profile")
