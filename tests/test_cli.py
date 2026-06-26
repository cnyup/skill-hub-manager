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

    def test_sync_command_dry_run_does_not_write_links_or_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skill = root / "skills" / "k8s-finder"
            stale = root / "skills" / "old-skill"
            skill.mkdir(parents=True)
            stale.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            (stale / "SKILL.md").write_text("# stale", encoding="utf-8")
            profile = root / "profiles" / "default.yaml"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "name: default\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )
            target = Path(temp_dir) / "target"
            target.mkdir()
            (target / "old-skill").symlink_to(stale, target_is_directory=True)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "sync",
                        "--root",
                        str(root),
                        "--target",
                        str(target),
                        "--dry-run",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertFalse((target / "k8s-finder").exists())
            self.assertTrue((target / "old-skill").is_symlink())
            self.assertFalse((root / "state" / "last-sync.json").exists())
            self.assertIn("would-link: k8s-finder", output.getvalue())
            self.assertIn("would-remove: old-skill", output.getvalue())

    def test_sync_command_records_removed_stale_links_in_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            current = root / "skills" / "k8s-finder"
            stale = root / "skills" / "old-skill"
            current.mkdir(parents=True)
            stale.mkdir(parents=True)
            (current / "SKILL.md").write_text("# current", encoding="utf-8")
            (stale / "SKILL.md").write_text("# stale", encoding="utf-8")
            profile = root / "profiles" / "default.yaml"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "name: default\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )
            target = Path(temp_dir) / "target"
            target.mkdir()
            (target / "old-skill").symlink_to(stale, target_is_directory=True)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["sync", "--root", str(root), "--target", str(target)])

            state = (root / "state" / "last-sync.json").read_text(encoding="utf-8")
            self.assertEqual(exit_code, 0)
            self.assertIn('"removed": [', state)
            self.assertIn('"old-skill"', state)

    def test_sync_command_respects_profile_exclude(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            kept = root / "skills" / "k8s-finder"
            excluded = root / "skills" / "billing-labeler"
            kept.mkdir(parents=True)
            excluded.mkdir(parents=True)
            (kept / "SKILL.md").write_text("# kept", encoding="utf-8")
            (excluded / "SKILL.md").write_text("# excluded", encoding="utf-8")
            profile = root / "profiles" / "default.yaml"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - billing-labeler\n"
                "exclude:\n"
                "  - billing-labeler\n",
                encoding="utf-8",
            )
            target = Path(temp_dir) / "target"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["sync", "--root", str(root), "--target", str(target)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((target / "k8s-finder").is_symlink())
            self.assertFalse((target / "billing-labeler").exists())

    def test_sync_command_respects_glob_profile_exclude(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            kept = root / "skills" / "k8s-finder"
            experimental = root / "skills" / "experimental-k8s"
            kept.mkdir(parents=True)
            experimental.mkdir(parents=True)
            (kept / "SKILL.md").write_text("# kept", encoding="utf-8")
            (experimental / "SKILL.md").write_text("# excluded", encoding="utf-8")
            profile = root / "profiles" / "default.yaml"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - experimental-k8s\n"
                "exclude:\n"
                "  - experimental-*\n",
                encoding="utf-8",
            )
            target = Path(temp_dir) / "target"

            exit_code = main(["sync", "--root", str(root), "--target", str(target)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((target / "k8s-finder").is_symlink())
            self.assertFalse((target / "experimental-k8s").exists())

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

    def test_ls_command_prints_registry_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skills = root / "skills"
            alpha = skills / "alpha-skill"
            zebra = skills / "zebra-skill"
            alpha.mkdir(parents=True)
            zebra.mkdir(parents=True)
            (alpha / "SKILL.md").write_text("---\nname: alpha-skill\nvisibility: team\n---\n", encoding="utf-8")
            (zebra / "SKILL.md").write_text("---\nname: zebra-skill\nvisibility: private\n---\n", encoding="utf-8")
            main(["registry", "build", "--root", str(root)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["ls", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip().splitlines(), ["alpha-skill", "zebra-skill"])

    def test_find_command_searches_registry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skills = root / "skills"
            finder = skills / "k8s-finder"
            labeler = skills / "billing-labeler"
            finder.mkdir(parents=True)
            labeler.mkdir(parents=True)
            (finder / "SKILL.md").write_text(
                "---\nname: k8s-finder\ndescription: Find Kubernetes services\ntags:\n  - infra\n  - kubernetes\nvisibility: team\n---\n",
                encoding="utf-8",
            )
            (labeler / "SKILL.md").write_text(
                "---\nname: billing-labeler\ndescription: Label billing rows\nvisibility: private\n---\n",
                encoding="utf-8",
            )
            main(["registry", "build", "--root", str(root)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["find", "--root", str(root), "--query", "kubernetes"])

            self.assertEqual(exit_code, 0)
            self.assertIn("k8s-finder", output.getvalue())
            self.assertNotIn("billing-labeler", output.getvalue())

    def test_profile_list_command_shows_workspace_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "zebra.yaml").write_text("name: zebra\nagent: codex\nskills:\n", encoding="utf-8")
            (profiles / "alpha.yaml").write_text("name: alpha\nagent: codex\nskills:\n", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "list", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue().strip().splitlines(), ["alpha", "zebra"])

    def test_profile_show_command_prints_effective_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - experimental-k8s\n"
                "exclude:\n"
                "  - experimental-*\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "show", "--root", str(root), "--name", "default"])

            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("name: default", rendered)
            self.assertIn("agent: codex", rendered)
            self.assertIn("effective_skills: [k8s-finder]", rendered)

    def test_profile_add_command_writes_profile_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile",
                        "add",
                        "--root",
                        str(root),
                        "--name",
                        "default",
                        "--agent",
                        "codex",
                        "--skill",
                        "billing-labeler",
                        "--skill",
                        "k8s-finder",
                        "--exclude",
                        "experimental-*",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "profiles" / "default.yaml").read_text(encoding="utf-8"),
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - billing-labeler\n"
                "  - k8s-finder\n"
                "exclude:\n"
                "  - experimental-*\n",
            )
            self.assertIn("wrote:", output.getvalue())

    def test_profile_remove_command_deletes_profile_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "remove", "--root", str(root), "--name", "default"])

            self.assertEqual(exit_code, 0)
            self.assertFalse((profiles / "default.yaml").exists())
            self.assertIn("removed:", output.getvalue())

    def test_profile_update_command_updates_existing_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - billing-labeler\n"
                "exclude:\n"
                "  - experimental-*\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile",
                        "update",
                        "--root",
                        str(root),
                        "--name",
                        "default",
                        "--agent",
                        "claude",
                        "--add-skill",
                        "release-checker",
                        "--remove-skill",
                        "billing-labeler",
                        "--add-exclude",
                        "legacy-*",
                        "--remove-exclude",
                        "experimental-*",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (profiles / "default.yaml").read_text(encoding="utf-8"),
                "name: default\n"
                "agent: claude\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - release-checker\n"
                "exclude:\n"
                "  - legacy-*\n",
            )
            self.assertIn("updated:", output.getvalue())

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

    def test_audit_command_reports_profile_skill_exposure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skills = root / "skills"
            profiles = root / "profiles"
            skills.mkdir(parents=True)
            profiles.mkdir(parents=True)
            (skills / "k8s-finder").mkdir()
            (skills / "k8s-finder" / "SKILL.md").write_text("# skill", encoding="utf-8")
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - missing-skill\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["audit", "--root", str(root)])

            rendered = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("profile: default", rendered)
            self.assertIn("effective_skills: [k8s-finder, missing-skill]", rendered)
            self.assertIn("missing_skills: [missing-skill]", rendered)
