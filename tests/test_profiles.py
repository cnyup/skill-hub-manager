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

    def test_load_profile_reads_exclude_and_filters_effective_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project-a.yaml"
            path.write_text(
                "name: project-a\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - billing-labeler\n"
                "exclude:\n"
                "  - billing-labeler\n",
                encoding="utf-8",
            )

            profile = load_profile(path)

        self.assertEqual(profile.exclude, ["billing-labeler"])
        self.assertEqual(profile.effective_skills(), ["k8s-finder"])
