from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_hub_manager.install_state import find_install_record, load_install_records
from skill_hub_manager.paths import install_state_file


BUILTIN_TARGETS: dict[str, Path] = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}


@dataclass(frozen=True)
class DetectionResult:
    agent: str | None
    detected: bool
    confidence: str
    target_dir: Path | None
    reason: str


def detect_agent_target(root: Path, agent_hint: str | None) -> DetectionResult:
    if agent_hint:
        record = find_install_record(load_install_records(install_state_file(root)), agent_hint)
        if record and record.get("target_dir"):
            return DetectionResult(
                agent=agent_hint,
                detected=True,
                confidence="high",
                target_dir=Path(record["target_dir"]),
                reason="previous-install-record",
            )
        if agent_hint in BUILTIN_TARGETS:
            return DetectionResult(
                agent=agent_hint,
                detected=True,
                confidence="medium",
                target_dir=BUILTIN_TARGETS[agent_hint],
                reason="builtin-agent-mapping",
            )
    return DetectionResult(
        agent=agent_hint,
        detected=False,
        confidence="low",
        target_dir=None,
        reason="no-known-agent-target",
    )
