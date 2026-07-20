import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.agents import detect_agent_target
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

    def test_unknown_agent_returns_manual_confirmation_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = detect_agent_target(root=Path(temp_dir), agent_hint="unknown-agent")

        self.assertFalse(result.detected)
        self.assertEqual(result.confidence, "low")
        self.assertIsNone(result.target_dir)
        self.assertEqual(result.reason, "no-known-agent-target")

    def test_opencode_uses_its_global_skills_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = detect_agent_target(root=Path(temp_dir), agent_hint="opencode")

        self.assertEqual(result.agent, "opencode")
        self.assertTrue(result.detected)
        self.assertEqual(result.confidence, "medium")
        self.assertEqual(result.target_dir, Path.home() / ".config" / "opencode" / "skills")
        self.assertEqual(result.reason, "builtin-agent-mapping")

    def test_multiple_records_for_one_agent_require_manual_target_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_install_records(
                install_state_file(root),
                [
                    {"agent": "opencode", "profile": "project-a", "target_dir": "/tmp/a"},
                    {"agent": "opencode", "profile": "project-b", "target_dir": "/tmp/b"},
                ],
            )

            result = detect_agent_target(root=root, agent_hint="opencode")

        self.assertFalse(result.detected)
        self.assertIsNone(result.target_dir)
        self.assertEqual(result.reason, "ambiguous-install-record")


if __name__ == "__main__":
    unittest.main()
