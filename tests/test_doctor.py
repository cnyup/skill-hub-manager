import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.cli import main
from skill_hub_manager.doctor import find_broken_links


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
