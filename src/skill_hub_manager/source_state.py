from __future__ import annotations

import json
from pathlib import Path

from skill_hub_manager.state_io import atomic_write_text


def load_source_records(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    return [dict(record) for record in records]


def write_source_records(path: Path, records: list[dict[str, str]]) -> Path:
    return atomic_write_text(path, json.dumps({"records": records}, indent=2) + "\n")


def upsert_source_record(
    records: list[dict[str, str]],
    record: dict[str, str],
) -> list[dict[str, str]]:
    updated: list[dict[str, str]] = []
    replaced = False
    for existing in records:
        if existing.get("skill") == record.get("skill"):
            if not replaced:
                updated.append(dict(record))
                replaced = True
            continue
        updated.append(dict(existing))
    if not replaced:
        updated.append(dict(record))
    return updated


def find_source_record(records: list[dict[str, str]], skill: str) -> dict[str, str] | None:
    for record in records:
        if record.get("skill") == skill:
            return record
    return None


def remove_source_record(records: list[dict[str, str]], skill: str) -> list[dict[str, str]]:
    """Remove the source record matching the given skill name."""
    return [dict(record) for record in records if record.get("skill") != skill]
