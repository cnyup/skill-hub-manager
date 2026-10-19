import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.agents import detect_agent_target, list_agent_targets
from skill_hub_manager.install_state import write_install_records
from skill_hub_manager.paths import install_state_file


class AgentDetectionTests(unittest.TestCase):
    def test_previous_record_wins_over_builtin_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = install_state_file(root)
            write_install_records(
                state_file,
                [
                    {
                        "agent": "codex",
                        "profile": "codex",
                        "target_dir": "/tmp/custom-codex-skills",
                        "manager_path": "/tmp/skill-hub-manager",
                        "manager_repo": "https://github.com/cnyup/skill-hub-manager.git",
                        "manager_revision": "abc123",
                        "installed_at": "2026-06-30T10:00:00Z",
                        "detection_confidence": "high",
                        "detection_reason": "previous-install-record",
                    }
                ],
            )

            result = detect_agent_target(root=root, agent_hint="codex")

        self.assertEqual(result.agent, "codex")
        self.assertTrue(result.detected)
        self.assertEqual(result.confidence, "high")
        self.assertEqual(result.target_dir, Path("/tmp/custom-codex-skills"))
        self.assertEqual(result.reason, "previous-install-record")

    def test_list_agent_targets_includes_builtins_and_workspace_overrides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "agents.yaml").write_text(
                "custom-agent: ~/custom-agent-skills\n",
                encoding="utf-8",
            )

            targets = list_agent_targets(root)

        self.assertIn("codex", targets)
        self.assertEqual(targets["codex"], Path.home() / ".codex" / "skills")
        self.assertEqual(targets["custom-agent"], Path.home() / "custom-agent-skills")
        self.assertEqual(targets["claude"], Path.home() / ".claude" / "skills")
        self.assertNotIn("claude-code", targets)

    def test_claude_code_hint_returns_canonical_claude_agent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = detect_agent_target(root=Path(temp_dir), agent_hint="claude-code")

        self.assertEqual(result.agent, "claude")
        self.assertTrue(result.detected)
        self.assertEqual(result.target_dir, Path.home() / ".claude" / "skills")

    def test_claude_code_legacy_install_record_remains_compatible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_install_records(
                install_state_file(root),
                [{
                    "agent": "claude-code",
                    "profile": "claude-code",
                    "target_dir": "/tmp/legacy-claude-skills",
                }],
            )

            result = detect_agent_target(root=root, agent_hint="claude")

        self.assertEqual(result.agent, "claude")
        self.assertTrue(result.detected)
        self.assertEqual(result.target_dir, Path("/tmp/legacy-claude-skills"))
        self.assertEqual(result.reason, "previous-install-record")

    def test_unknown_agent_returns_manual_confirmation_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = detect_agent_target(root=Path(temp_dir), agent_hint="unknown-agent")

        self.assertFalse(result.detected)
        self.assertEqual(result.confidence, "low")
        self.assertIsNone(result.target_dir)
        self.assertEqual(result.reason, "no-known-agent-target")


if __name__ == "__main__":
    unittest.main()
