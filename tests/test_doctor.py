import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.cli import main
from skill_hub_manager.doctor import find_broken_links, find_missing_expected_links, load_sync_target


class DoctorTests(unittest.TestCase):
    def test_find_broken_links_reports_missing_targets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            (target / "missing").symlink_to(root / "does-not-exist")

            broken = find_broken_links(target)

        self.assertEqual(broken, ["missing"])

    def test_doctor_command_uses_workspace_root_for_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            target = root / "skills"
            target.mkdir(parents=True)
            (target / "missing").symlink_to(root / "does-not-exist")

            exit_code = main(["doctor", "--root", str(root)])

        self.assertEqual(exit_code, 1)

    def test_find_missing_expected_links_reads_last_sync_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "skills"
            target.mkdir()
            state_dir = root / "state"
            state_dir.mkdir()
            (state_dir / "last-sync.json").write_text(
                "{\n"
                '  "profile": "default",\n'
                '  "agent": "codex",\n'
                '  "target": "/tmp/skills",\n'
                '  "linked": ["k8s-finder", "billing-labeler"],\n'
                '  "missing": []\n'
                "}\n",
                encoding="utf-8",
            )
            (target / "k8s-finder").symlink_to(root / "vault" / "k8s-finder")

            missing = find_missing_expected_links(target, state_dir / "last-sync.json")

        self.assertEqual(missing, ["billing-labeler"])

    def test_load_sync_target_reads_target_from_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state" / "last-sync.json"
            state_file.parent.mkdir()
            state_file.write_text(
                "{\n"
                '  "profile": "default",\n'
                '  "agent": "codex",\n'
                '  "target": "/tmp/custom-target",\n'
                '  "linked": ["k8s-finder"],\n'
                '  "missing": []\n'
                "}\n",
                encoding="utf-8",
            )

            target = load_sync_target(state_file)

        self.assertEqual(target, Path("/tmp/custom-target"))

    def test_doctor_command_uses_synced_target_from_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            state = root / "state"
            state.mkdir(parents=True)
            external_target = Path(temp_dir) / "external-target"
            external_target.mkdir()
            (state / "last-sync.json").write_text(
                "{\n"
                '  "profile": "default",\n'
                '  "agent": "codex",\n'
                f'  "target": "{external_target}",\n'
                '  "linked": ["k8s-finder"],\n'
                '  "missing": []\n'
                "}\n",
                encoding="utf-8",
            )

            exit_code = main(["doctor", "--root", str(root)])

        self.assertEqual(exit_code, 1)
