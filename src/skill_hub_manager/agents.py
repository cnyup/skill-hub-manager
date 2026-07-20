from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from skill_hub_manager.install_state import find_install_record, load_install_records
from skill_hub_manager.paths import install_state_file


# Built-in defaults — can be extended or overridden via ~/.skill-hub/agents.yaml
# or the SKILL_HUB_AGENTS environment variable (JSON format).
_DEFAULT_TARGETS: dict[str, Path] = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
    "claude-code": Path.home() / ".claude" / "skills",
    "cursor": Path.home() / ".cursor" / "skills",
    "windsurf": Path.home() / ".codeium" / "windsurf" / "skills",
    "opencode": Path.home() / ".config" / "opencode" / "skills",
}


def load_builtin_targets(workspace_root: Path | None = None) -> dict[str, Path]:
    """Load agent target directories.

    Merges built-in defaults with user overrides from:
    1. ~/.skill-hub/agents.yaml (if workspace_root is provided, checked there)
    2. SKILL_HUB_AGENTS environment variable (JSON: {"agent": "/path"})
    """
    targets = dict(_DEFAULT_TARGETS)

    env_value = os.environ.get("SKILL_HUB_AGENTS")
    if env_value:
        import json

        try:
            overrides = json.loads(env_value)
            for agent, path_str in overrides.items():
                targets[agent] = Path(path_str).expanduser()
        except (json.JSONDecodeError, TypeError):
            pass

    if workspace_root is not None:
        config_file = workspace_root / "agents.yaml"
        if config_file.is_file():
            for line in config_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                agent, path_str = line.split(":", 1)
                agent = agent.strip()
                path_str = path_str.strip()
                if agent and path_str:
                    targets[agent] = Path(path_str).expanduser()

    return targets


@dataclass(frozen=True)
class DetectionResult:
    agent: str | None
    detected: bool
    confidence: str
    target_dir: Path | None
    reason: str


def detect_agent_target(root: Path, agent_hint: str | None) -> DetectionResult:
    if agent_hint:
        records = load_install_records(install_state_file(root))
        matches = [record for record in records if record.get("agent") == agent_hint]
        if len(matches) > 1:
            return DetectionResult(
                agent=agent_hint,
                detected=False,
                confidence="low",
                target_dir=None,
                reason="ambiguous-install-record",
            )
        record = find_install_record(records, agent_hint)
        if record and record.get("target_dir"):
            return DetectionResult(
                agent=agent_hint,
                detected=True,
                confidence="high",
                target_dir=Path(record["target_dir"]),
                reason="previous-install-record",
            )
        builtin_targets = load_builtin_targets(root)
        if agent_hint in builtin_targets:
            return DetectionResult(
                agent=agent_hint,
                detected=True,
                confidence="medium",
                target_dir=builtin_targets[agent_hint],
                reason="builtin-agent-mapping",
            )
    return DetectionResult(
        agent=agent_hint,
        detected=False,
        confidence="low",
        target_dir=None,
        reason="no-known-agent-target",
    )
