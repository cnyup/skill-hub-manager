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
