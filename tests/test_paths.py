import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.paths import initialize_workspace


class WorkspacePathTests(unittest.TestCase):
    def test_initialize_workspace_creates_expected_directories(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"

            paths = initialize_workspace(root)

            self.assertEqual(paths.root, root)
            self.assertTrue(paths.skills.is_dir())
            self.assertTrue(paths.profiles.is_dir())
            self.assertTrue(paths.state.is_dir())
            self.assertEqual(
                (paths.profiles / "default.yaml").read_text(encoding="utf-8"),
                "name: default\nagent: codex\nskills:\n",
            )
