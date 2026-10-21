from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from skill_hub_manager.fsutil import atomic_write_text
from skill_hub_manager.install_state import find_install_record, load_install_records
from skill_hub_manager.paths import install_state_file
from skill_hub_manager.profiles import load_profile


# Built-in defaults — can be extended or overridden via ~/.skill-hub/agents.yaml
# or the SKILL_HUB_AGENTS environment variable (JSON format).
_DEFAULT_TARGETS: dict[str, Path] = {
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
    "cursor": Path.home() / ".cursor" / "skills",
    "windsurf": Path.home() / ".codeium" / "windsurf" / "skills",
}

# Scan candidates for local agent discovery (Wave 6). Data table, not logic —
# adding a new agent only touches this mapping. skill-hub is the single shared
# manager; third-party common areas (e.g. ~/.agents/skills) are intentionally
# not scanned.
SCAN_CANDIDATES: dict[str, Path] = {
    **_DEFAULT_TARGETS,
    "opencode": Path.home() / ".config" / "opencode" / "skills",
    "zcode": Path.home() / ".zcode" / "skills",
    "qoder": Path.home() / ".qoder" / "skills",
    "workbuddy": Path.home() / ".workbuddy-ai" / "skills",
    "tianshuharness": Path.home() / ".rivet" / "skills",
}

_AGENT_ALIASES = {"claude-code": "claude"}


def canonical_agent_name(agent: str) -> str:
    return _AGENT_ALIASES.get(agent, agent)


def _agent_lookup_names(agent: str) -> tuple[str, ...]:
    canonical = canonical_agent_name(agent)
    aliases = tuple(alias for alias, target in _AGENT_ALIASES.items() if target == canonical)
    return (canonical, *aliases)


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
                targets[canonical_agent_name(agent)] = Path(path_str).expanduser()
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
                    targets[canonical_agent_name(agent)] = Path(path_str).expanduser()

    return targets


def list_agent_targets(workspace_root: Path | None = None) -> dict[str, Path]:
    """Return the configured Agent-to-skills-directory mapping."""
    return load_builtin_targets(workspace_root)


@dataclass(frozen=True)
class DetectionResult:
    agent: str | None
    detected: bool
    confidence: str
    target_dir: Path | None
    reason: str


@dataclass(frozen=True)
class ScanCandidate:
    """One scan-candidate agent and its local discovery state."""

    agent: str
    path: Path
    exists: bool
    skill_count: int
    managed: bool


def scan_local_agents(workspace_root: Path | None = None) -> list[ScanCandidate]:
    """Probe the built-in scan table against the local filesystem.

    exists/skill_count reflect the on-disk state; managed marks agents already
    known to skill-hub (built-ins plus workspace agents.yaml entries).
    """
    managed = load_builtin_targets(workspace_root)
    out: list[ScanCandidate] = []
    for agent, path in SCAN_CANDIDATES.items():
        canonical = canonical_agent_name(agent)
        exists = path.is_dir()
        out.append(
            ScanCandidate(
                agent=canonical,
                path=path,
                exists=exists,
                skill_count=sum(1 for _ in path.glob("*/SKILL.md")) if exists else 0,
                managed=canonical in managed,
            )
        )
    return out


def add_agent_target(workspace_root: Path, agent: str, target: Path) -> Path:
    """Register (or update) an agent target in the workspace agents.yaml.

    Writes are atomic; comments and unrelated entries are preserved. Returns
    the config file path.
    """
    canonical = canonical_agent_name(agent)
    config = workspace_root / "agents.yaml"
    lines: list[str] = []
    if config.is_file():
        for raw in config.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if stripped and not stripped.startswith("#") and ":" in stripped:
                if stripped.split(":", 1)[0].strip() == canonical:
                    continue  # drop the old entry for this agent; re-append below
            lines.append(raw)
    lines.append(f"{canonical}: {target.expanduser()}")
    atomic_write_text(config, "\n".join(lines) + "\n")
    return config


def remove_agent_target(workspace_root: Path, agent: str) -> bool:
    """Unregister an agent target from the workspace agents.yaml.

    Built-in agents cannot be removed (they are code defaults). Returns True
    when an entry was actually dropped; False for built-ins and missing
    entries (idempotent no-op).
    """
    canonical = canonical_agent_name(agent)
    if canonical in _DEFAULT_TARGETS:
        return False
    config = workspace_root / "agents.yaml"
    if not config.is_file():
        return False
    kept: list[str] = []
    removed = False
    for raw in config.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and ":" in stripped:
            if stripped.split(":", 1)[0].strip() == canonical:
                removed = True
                continue  # drop this entry
        kept.append(raw)
    if not removed:
        return False
    atomic_write_text(config, "\n".join(kept).rstrip("\n") + ("\n" if kept else ""))
    _remove_agent_profiles(workspace_root, canonical)
    return True


def _remove_agent_profiles(workspace_root: Path, canonical_agent: str) -> list[str]:
    """Delete profile YAMLs belonging to the removed agent; return removed names.

    Without this cascade the Library badges (audit), the Agents panel and the
    sidebar Profiles list keep showing the removed agent.
    """
    profiles_dir = workspace_root / "profiles"
    if not profiles_dir.is_dir():
        return []
    dropped: list[str] = []
    for profile_path in sorted(profiles_dir.glob("*.yaml")):
        try:
            profile = load_profile(profile_path)
        except (OSError, ValueError):
            continue
        if canonical_agent_name(profile.agent) == canonical_agent:
            profile_path.unlink()
            dropped.append(profile.name)
    return dropped


def detect_agent_target(root: Path, agent_hint: str | None) -> DetectionResult:
    if agent_hint:
        canonical_agent = canonical_agent_name(agent_hint)
        records = load_install_records(install_state_file(root))
        record = next(
            (
                found
                for lookup_name in _agent_lookup_names(canonical_agent)
                if (found := find_install_record(records, lookup_name)) is not None
            ),
            None,
        )
        if record and record.get("target_dir"):
            return DetectionResult(
                agent=canonical_agent,
                detected=True,
                confidence="high",
                target_dir=Path(record["target_dir"]),
                reason="previous-install-record",
            )
        builtin_targets = load_builtin_targets(root)
        if canonical_agent in builtin_targets:
            return DetectionResult(
                agent=canonical_agent,
                detected=True,
                confidence="medium",
                target_dir=builtin_targets[canonical_agent],
                reason="builtin-agent-mapping",
            )
    return DetectionResult(
        agent=canonical_agent_name(agent_hint) if agent_hint else None,
        detected=False,
        confidence="low",
        target_dir=None,
        reason="no-known-agent-target",
    )
