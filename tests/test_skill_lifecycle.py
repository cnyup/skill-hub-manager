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

    def test_skill_remove_ghost_record_cleans_registry_and_references(self):
        """幽灵 skill：registry/source 记录还在但 vault 目录已被外部删除。

        remove 应清理 registry、profile 引用与来源记录并返回 0（幂等清理），
        而不是撞 FileNotFoundError 或报 missing 后留下脏记录。
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            (root / "skills").mkdir(parents=True)
            (root / "state").mkdir()
            # registry 里登记了已消失的 skill
            (root / "state" / "registry.yaml").write_text(
                "skills:\n  ghost-skill:\n    path: nowhere\n",
                encoding="utf-8",
            )
            # source 记录还在
            (root / "state" / "skill-sources.json").write_text(
                json.dumps({"records": [{"skill": "ghost-skill", "source": "/gone", "stored_path": "/gone/vault"}]}),
                encoding="utf-8",
            )
            # 一个 profile 还引用它
            (root / "profiles").mkdir()
            (root / "profiles" / "default.yaml").write_text(
                "name: default\nagent: codex\nskills:\n  - ghost-skill\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main([
                    "skill", "remove", "--root", str(root), "--name", "ghost-skill",
                    "--purge-source", "--json",
                ])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["skill"], "ghost-skill")
            self.assertFalse(payload["removed"])  # vault 里本来就不存在
            self.assertTrue(payload["purged_source"])
            self.assertEqual(payload["updated_profiles"], ["default"])
            # source 记录已清空
            records = json.loads((root / "state" / "skill-sources.json").read_text(encoding="utf-8"))
            self.assertEqual(records["records"], [])
            # profile 已移除引用
            profile_text = (root / "profiles" / "default.yaml").read_text(encoding="utf-8")
            self.assertNotIn("ghost-skill", profile_text)

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
