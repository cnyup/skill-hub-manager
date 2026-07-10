import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.cli import main


class SkillRemoveTests(unittest.TestCase):
    def test_skill_remove_deletes_vault_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "remove", "--root", str(root), "--name", "web-access"])

            self.assertEqual(exit_code, 0)
            self.assertFalse((root / "skills" / "web-access").exists())
            self.assertIn("removed: web-access", output.getvalue())

    def test_skill_remove_json_reports_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "remove", "--root", str(root), "--name", "web-access", "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["removed"])
            self.assertEqual(payload["skill"], "web-access")

    def test_skill_remove_missing_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()
            (root / "skills").mkdir()
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "remove", "--root", str(root), "--name", "nonexistent"])

            self.assertEqual(exit_code, 1)
            self.assertIn("missing: nonexistent", output.getvalue())

    def test_skill_remove_purges_source_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])

            main(["skill", "remove", "--root", str(root), "--name", "web-access", "--purge-source"])

            source_output = io.StringIO()
            with contextlib.redirect_stdout(source_output):
                main(["skill", "source", "list", "--root", str(root), "--json"])
            payload = json.loads(source_output.getvalue())
            self.assertEqual(payload["records"], [])

    def test_skill_remove_removes_from_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])
            main([
                "profile", "update", "--root", str(root),
                "--name", "default", "--add-skill", "web-access",
            ])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "remove", "--root", str(root), "--name", "web-access"])

            self.assertEqual(exit_code, 0)
            self.assertIn("updated_profiles: default", output.getvalue())
            profile_content = (root / "profiles" / "default.yaml").read_text(encoding="utf-8")
            self.assertNotIn("web-access", profile_content)

    def test_skill_remove_rebuilds_registry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])
            main(["registry", "build", "--root", str(root)])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "remove", "--root", str(root), "--name", "web-access"])

            self.assertEqual(exit_code, 0)
            self.assertIn("rebuilt: registry", output.getvalue())
            registry_content = (root / "state" / "registry.yaml").read_text(encoding="utf-8")
            self.assertNotIn("web-access", registry_content)


class SkillUpdateTests(unittest.TestCase):
    def test_skill_update_reimports_from_cached_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            cache = Path(temp_dir) / "cache" / "my-skill"
            cache.mkdir(parents=True)
            (cache / "SKILL.md").write_text("---\nname: my-skill\ndescription: v1\n---\n", encoding="utf-8")
            main([
                "skill", "import", "--root", str(root), "--source", str(cache),
                "--cache-checkout", str(cache),
            ])

            (cache / "SKILL.md").write_text("---\nname: my-skill\ndescription: v2\n---\n", encoding="utf-8")

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "update", "--root", str(root), "--name", "my-skill", "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["replaced"])
            vault_content = (root / "skills" / "my-skill" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("v2", vault_content)

    def test_skill_update_missing_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir()
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "update", "--root", str(root), "--name", "nonexistent", "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["updated"])


class ScanJsonTests(unittest.TestCase):
    def test_scan_json_outputs_skill_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            skill = vault / "alpha"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["scan", "--vault", str(vault), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["skills"], ["alpha"])


if __name__ == "__main__":
    unittest.main()
