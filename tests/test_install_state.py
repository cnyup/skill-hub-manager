import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.install_state import (
    find_install_record,
    load_install_records,
    upsert_install_record,
    write_install_records,
)
from skill_hub_manager.paths import install_state_file


class InstallStateTests(unittest.TestCase):
    def test_install_state_round_trip_and_lookup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = install_state_file(root)
            records = [
                {
                    "agent": "codex",
                    "profile": "codex",
                    "target_dir": "/tmp/codex-skills",
                    "manager_path": "/tmp/skill-hub-manager",
                    "manager_repo": "https://github.com/cnyup/skill-hub-manager.git",
                    "manager_revision": "abc123",
                    "installed_at": "2026-06-30T10:00:00Z",
                    "detection_confidence": "high",
                    "detection_reason": "previous-install-record",
                },
                {
                    "agent": "claude",
                    "profile": "claude",
                    "target_dir": "/tmp/claude-skills",
                    "manager_path": "/tmp/skill-hub-manager",
                    "manager_repo": "https://github.com/cnyup/skill-hub-manager.git",
                    "manager_revision": "def456",
                    "installed_at": "2026-06-30T11:00:00Z",
                    "detection_confidence": "medium",
                    "detection_reason": "builtin-agent-mapping",
                },
            ]

            write_install_records(state_file, records)
            loaded = load_install_records(state_file)
            found = find_install_record(loaded, "claude")

        self.assertEqual(loaded, records)
        self.assertEqual(found, records[1])

    def test_upsert_install_record_replaces_matching_agent_and_profile(self):
        existing = [
            {
                "agent": "codex",
                "profile": "codex",
                "target_dir": "/tmp/old",
                "manager_path": "/tmp/skill-hub-manager",
                "manager_repo": "https://github.com/cnyup/skill-hub-manager.git",
                "manager_revision": "abc123",
                "installed_at": "2026-06-30T10:00:00Z",
                "detection_confidence": "high",
                "detection_reason": "previous-install-record",
            }
        ]
        updated = upsert_install_record(
            existing,
            {
                "agent": "codex",
                "profile": "codex",
                "target_dir": "/tmp/new",
                "manager_path": "/tmp/skill-hub-manager",
                "manager_repo": "https://github.com/cnyup/skill-hub-manager.git",
                "manager_revision": "xyz789",
                "installed_at": "2026-06-30T12:00:00Z",
                "detection_confidence": "high",
                "detection_reason": "previous-install-record",
            },
        )

        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["target_dir"], "/tmp/new")


if __name__ == "__main__":
    unittest.main()
