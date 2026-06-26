import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.profiles import Profile
from skill_hub_manager.skills import Skill
from skill_hub_manager.sync import sync_profile


class SyncTests(unittest.TestCase):
    def test_sync_profile_links_profile_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vault" / "k8s-finder"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("# skill", encoding="utf-8")
            target = root / "target"
            profile = Profile(name="project-a", agent="codex", skills=["k8s-finder"])
            skills = {"k8s-finder": Skill(name="k8s-finder", path=source)}

            result = sync_profile(profile, skills, target)

            self.assertEqual(result.linked, ["k8s-finder"])
            self.assertEqual(result.missing, [])
            self.assertTrue((target / "k8s-finder").is_symlink())
            self.assertEqual((target / "k8s-finder").resolve(), source.resolve())
