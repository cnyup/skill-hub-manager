import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.profiles import load_profile


class ProfileTests(unittest.TestCase):
    def test_load_profile_reads_name_agent_and_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project-a.yaml"
            path.write_text(
                "name: project-a\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )

            profile = load_profile(path)

        self.assertEqual(profile.name, "project-a")
        self.assertEqual(profile.agent, "codex")
        self.assertEqual(profile.skills, ["k8s-finder"])
