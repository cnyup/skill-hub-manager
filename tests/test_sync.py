import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.profiles import Profile
from skill_hub_manager.skills import Skill
from skill_hub_manager.sync import render_sync_result_json, sync_profile, write_sync_state


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
            self.assertEqual(result.removed, [])
            self.assertTrue((target / "k8s-finder").is_symlink())
            self.assertEqual((target / "k8s-finder").resolve(), source.resolve())

    def test_sync_profile_removes_stale_symlinks_not_in_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "vault"
            current = vault / "k8s-finder"
            stale = vault / "old-skill"
            current.mkdir(parents=True)
            stale.mkdir(parents=True)
            (current / "SKILL.md").write_text("# current", encoding="utf-8")
            (stale / "SKILL.md").write_text("# stale", encoding="utf-8")
            target = root / "target"
            target.mkdir()
            (target / "old-skill").symlink_to(stale, target_is_directory=True)
            profile = Profile(name="project-a", agent="codex", skills=["k8s-finder"])
            skills = {"k8s-finder": Skill(name="k8s-finder", path=current)}

            result = sync_profile(profile, skills, target)

            self.assertEqual(result.linked, ["k8s-finder"])
            self.assertEqual(result.missing, [])
            self.assertEqual(result.removed, ["old-skill"])
            self.assertFalse((target / "old-skill").exists())

    def test_sync_profile_preserves_regular_files_not_in_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "vault" / "k8s-finder"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("# skill", encoding="utf-8")
            target = root / "target"
            target.mkdir()
            (target / "notes.txt").write_text("keep me", encoding="utf-8")
            profile = Profile(name="project-a", agent="codex", skills=["k8s-finder"])
            skills = {"k8s-finder": Skill(name="k8s-finder", path=source)}

            result = sync_profile(profile, skills, target)

            self.assertEqual(result.removed, [])
            self.assertTrue((target / "notes.txt").is_file())

    def test_sync_profile_dry_run_reports_changes_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "vault"
            current = vault / "k8s-finder"
            stale = vault / "old-skill"
            current.mkdir(parents=True)
            stale.mkdir(parents=True)
            (current / "SKILL.md").write_text("# current", encoding="utf-8")
            (stale / "SKILL.md").write_text("# stale", encoding="utf-8")
            target = root / "target"
            target.mkdir()
            (target / "old-skill").symlink_to(stale, target_is_directory=True)
            profile = Profile(name="project-a", agent="codex", skills=["k8s-finder"])
            skills = {"k8s-finder": Skill(name="k8s-finder", path=current)}

            result = sync_profile(profile, skills, target, dry_run=True)

            self.assertEqual(result.linked, ["k8s-finder"])
            self.assertEqual(result.removed, ["old-skill"])
            self.assertFalse((target / "k8s-finder").exists())
            self.assertTrue((target / "old-skill").is_symlink())

    def test_write_sync_state_records_profile_and_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state_file = root / "state" / "last-sync.json"
            profile = Profile(name="default", agent="codex", skills=["k8s-finder"])

            write_sync_state(
                state_file=state_file,
                profile=profile,
                target=root / "target",
                linked=["k8s-finder"],
                missing=["missing-skill"],
                removed=["old-skill"],
            )

            content = state_file.read_text(encoding="utf-8")
            self.assertIn('"profile": "default"', content)
            self.assertIn('"agent": "codex"', content)
            self.assertIn('"linked": [', content)
            self.assertIn('"missing": [', content)
            self.assertIn('"removed": [', content)

    def test_render_sync_result_json_returns_stable_payload(self):
        profile = Profile(name="default", agent="codex", skills=["k8s-finder"])
        result = render_sync_result_json(
            profile=profile,
            target=Path("/tmp/skills"),
            linked=["k8s-finder"],
            missing=["missing-skill"],
            removed=["old-skill"],
            dry_run=True,
        )

        self.assertEqual(
            result,
            '{\n'
            '  "mode": "dry-run",\n'
            '  "profile": "default",\n'
            '  "agent": "codex",\n'
            '  "target": "/tmp/skills",\n'
            '  "linked": [\n'
            '    "k8s-finder"\n'
            '  ],\n'
            '  "missing": [\n'
            '    "missing-skill"\n'
            '  ],\n'
            '  "removed": [\n'
            '    "old-skill"\n'
            '  ]\n'
            '}',
        )
