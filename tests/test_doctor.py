import tempfile
import unittest
from pathlib import Path

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
