import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.cli import main


class CliTests(unittest.TestCase):
    def test_cli_version_prints_package_name(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = main(["--version"])

        self.assertEqual(exit_code, 0)
        self.assertIn("skill-hub", output.getvalue())

    def test_scan_command_lists_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill = root / "vault" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["scan", "--vault", str(root / "vault")])

        self.assertEqual(exit_code, 0)
        self.assertIn("k8s-finder", output.getvalue())

    def test_scan_command_uses_workspace_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skill = root / "skills" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["scan", "--root", str(root)])

        self.assertEqual(exit_code, 0)
        self.assertIn("k8s-finder", output.getvalue())

    def test_sync_command_links_profile_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill = root / "vault" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            profile = root / "project-a.yaml"
            profile.write_text(
                "name: project-a\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )
            target = root / "target"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "sync",
                        "--vault",
                        str(root / "vault"),
                        "--profile",
                        str(profile),
                        "--target",
                        str(target),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target / "k8s-finder").is_symlink())
            self.assertIn("linked: k8s-finder", output.getvalue())

    def test_sync_command_uses_workspace_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skill = root / "skills" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            profile = root / "profiles" / "default.yaml"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "name: default\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )
            target = Path(temp_dir) / "target"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "sync",
                        "--root",
                        str(root),
                        "--target",
                        str(target),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((target / "k8s-finder").is_symlink())
            self.assertIn("linked: k8s-finder", output.getvalue())
            self.assertTrue((root / "state" / "last-sync.json").is_file())

    def test_doctor_command_reports_broken_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            (target / "missing").symlink_to(root / "does-not-exist")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["doctor", "--target", str(target)])

        self.assertEqual(exit_code, 1)
        self.assertIn("broken: missing", output.getvalue())

    def test_init_command_creates_local_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["init", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((root / "skills").is_dir())
            self.assertTrue((root / "profiles").is_dir())
            self.assertTrue((root / "state").is_dir())
            self.assertTrue((root / "profiles" / "default.yaml").is_file())
            self.assertIn("initialized:", output.getvalue())

    def test_registry_build_command_writes_registry_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "skills"
            skill = vault / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            output_path = root / "state" / "registry.yaml"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "registry",
                        "build",
                        "--vault",
                        str(vault),
                        "--output",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.is_file())
            self.assertIn("skills:", output_path.read_text(encoding="utf-8"))
            self.assertIn("k8s-finder:", output_path.read_text(encoding="utf-8"))
            self.assertIn("wrote:", output.getvalue())

    def test_registry_build_command_uses_workspace_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skill = root / "skills" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["registry", "build", "--root", str(root)])

            output_path = root / "state" / "registry.yaml"
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.is_file())
            self.assertIn("k8s-finder:", output_path.read_text(encoding="utf-8"))

    def test_doctor_command_reports_missing_expected_links_from_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            target = root / "skills"
            target.mkdir(parents=True)
            state = root / "state"
            state.mkdir()
            (state / "last-sync.json").write_text(
                "{\n"
                '  "profile": "default",\n'
                '  "agent": "codex",\n'
                '  "target": "/tmp/skills",\n'
                '  "linked": ["k8s-finder"],\n'
                '  "missing": []\n'
                "}\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["doctor", "--root", str(root)])

            self.assertEqual(exit_code, 1)
            self.assertIn("expected-missing: k8s-finder", output.getvalue())
