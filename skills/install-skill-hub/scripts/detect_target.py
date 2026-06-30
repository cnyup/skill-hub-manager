from __future__ import annotations

import json
import sys
from pathlib import Path


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from skill_hub_manager.agents import detect_agent_target


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("usage: detect_target.py <workspace-root> [agent]")

    root = Path(args[0]).expanduser()
    agent = args[1] if len(args) > 1 else None
    result = detect_agent_target(root=root, agent_hint=agent)
    print(
        json.dumps(
            {
                "agent": result.agent,
                "detected": result.detected,
                "confidence": result.confidence,
                "target_dir": None if result.target_dir is None else str(result.target_dir),
                "reason": result.reason,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
