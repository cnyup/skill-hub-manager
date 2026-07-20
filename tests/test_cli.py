import contextlib
import io
import json
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

    def test_agent_detect_json_output_for_builtin_mapping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["agent", "detect", "--root", str(root), "--agent", "codex", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["detected"])
        self.assertEqual(payload["agent"], "codex")
        self.assertEqual(payload["confidence"], "medium")
        self.assertEqual(payload["reason"], "builtin-agent-mapping")
        self.assertEqual(payload["target_dir"], str(Path.home() / ".codex" / "skills"))

    def test_agent_detect_json_output_for_opencode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["agent", "detect", "--root", str(root), "--agent", "opencode", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["detected"])
        self.assertEqual(payload["agent"], "opencode")
        self.assertEqual(payload["confidence"], "medium")
        self.assertEqual(payload["reason"], "builtin-agent-mapping")
        self.assertEqual(payload["target_dir"], str(Path.home() / ".config" / "opencode" / "skills"))

    def test_install_state_record_and_show_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            record_output = io.StringIO()

            with contextlib.redirect_stdout(record_output):
                record_exit_code = main(
                    [
                        "install-state",
                        "record",
                        "--root",
                        str(root),
                        "--agent",
                        "codex",
                        "--profile",
                        "codex",
                        "--target",
                        "/tmp/codex-skills",
                        "--manager-path",
                        "/tmp/skill-hub-manager",
                        "--manager-repo",
                        "https://github.com/cnyup/skill-hub-manager.git",
                        "--manager-revision",
                        "abc123",
                        "--detection-confidence",
                        "high",
                        "--detection-reason",
                        "previous-install-record",
                    ]
                )

            show_output = io.StringIO()
            with contextlib.redirect_stdout(show_output):
                show_exit_code = main(["install-state", "show", "--root", str(root), "--agent", "codex", "--json"])

        payload = json.loads(show_output.getvalue())
        self.assertEqual(record_exit_code, 0)
        self.assertEqual(show_exit_code, 0)
        self.assertIn("recorded:", record_output.getvalue())
        self.assertEqual(payload["record"]["agent"], "codex")
        self.assertEqual(payload["record"]["profile"], "codex")
        self.assertEqual(payload["record"]["target_dir"], "/tmp/codex-skills")
        self.assertEqual(payload["record"]["manager_path"], "/tmp/skill-hub-manager")
        self.assertEqual(payload["record"]["manager_repo"], "https://github.com/cnyup/skill-hub-manager.git")
        self.assertEqual(payload["record"]["manager_revision"], "abc123")
        self.assertEqual(payload["record"]["detection_confidence"], "high")
        self.assertEqual(payload["record"]["detection_reason"], "previous-install-record")
        self.assertEqual(payload["records"], [payload["record"]])

    def test_install_state_show_json_missing_agent_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["install-state", "show", "--root", str(root), "--agent", "codex", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["records"], [])
        self.assertIsNone(payload["record"])

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

    def test_skill_import_copies_local_skill_into_workspace_and_records_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "skill",
                        "import",
                        "--root",
                        str(root),
                        "--source",
                        str(source),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((root / "skills" / "web-access" / "SKILL.md").is_file())
            self.assertTrue((root / "state" / "skill-sources.json").is_file())
            self.assertIn("imported: web-access", output.getvalue())

    def test_skill_import_json_reports_replacement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])
            (source / "NOTES.txt").write_text("updated", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "skill",
                        "import",
                        "--root",
                        str(root),
                        "--source",
                        str(source),
                        "--force",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["replaced"])
            self.assertEqual(payload["skill"], "web-access")

    def test_skill_import_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "skill",
                        "import",
                        "--root",
                        str(root),
                        "--source",
                        str(source),
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("exists:", output.getvalue())

    def test_skill_import_json_reports_missing_skill_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "skill",
                        "import",
                        "--root",
                        str(root),
                        "--source",
                        str(source),
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["replaced"])
            self.assertEqual(payload["skill"], "web-access")
            self.assertIn("missing SKILL.md", payload["error"])

    def test_skill_source_list_does_not_initialize_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "source", "list", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(output.getvalue(), "")
            self.assertFalse((root / "profiles" / "default.yaml").exists())

    def test_skill_source_show_missing_does_not_initialize_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "skill",
                        "source",
                        "show",
                        "--root",
                        str(root),
                        "--name",
                        "web-access",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("missing: web-access", output.getvalue())
            self.assertFalse((root / "profiles" / "default.yaml").exists())

    def test_skill_source_show_returns_record_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(
                [
                    "skill",
                    "import",
                    "--root",
                    str(root),
                    "--source",
                    str(source),
                    "--source-ref",
                    "file:///tmp/example.git",
                    "--source-type",
                    "git-repo",
                    "--repo-url",
                    "file:///tmp/example.git",
                    "--git-ref",
                    "release",
                    "--cache-checkout",
                    "/tmp/cache/example",
                    "--import-subpath",
                    "skills/web-access",
                ]
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "skill",
                        "source",
                        "show",
                        "--root",
                        str(root),
                        "--name",
                        "web-access",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["record"]["source_type"], "git-repo")
            self.assertEqual(payload["record"]["repo_url"], "file:///tmp/example.git")
            self.assertEqual(payload["record"]["git_ref"], "release")
            self.assertEqual(payload["record"]["import_subpath"], "skills/web-access")

    def test_skill_source_list_prints_imported_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "incoming" / "web-access"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")
            main(["skill", "import", "--root", str(root), "--source", str(source)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["skill", "source", "list", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertIn("web-access", output.getvalue())

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

    def test_sync_command_json_outputs_machine_readable_apply_result(self):
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
                exit_code = main(["sync", "--root", str(root), "--target", str(target), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["mode"], "apply")
            self.assertEqual(payload["profile"], "default")
            self.assertEqual(payload["agent"], "codex")
            self.assertEqual(payload["target"], str(target))
            self.assertEqual(payload["linked"], ["k8s-finder"])
            self.assertEqual(payload["missing"], [])
            self.assertEqual(payload["removed"], [])

    def test_sync_command_json_outputs_machine_readable_dry_run_result(self):
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
                    ["sync", "--root", str(root), "--target", str(target), "--dry-run", "--json"]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["mode"], "dry-run")
            self.assertEqual(payload["linked"], ["k8s-finder"])
            self.assertEqual(payload["missing"], [])
            self.assertEqual(payload["removed"], ["old-skill"])
            self.assertFalse((root / "state" / "last-sync.json").exists())

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
            self.assertTrue((root / "sources").is_dir())
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

    def test_registry_doctor_command_reports_registry_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skills = root / "skills"
            state = root / "state"
            skills.mkdir(parents=True)
            state.mkdir(parents=True)
            current = skills / "k8s-finder"
            current.mkdir()
            (current / "SKILL.md").write_text("---\nname: k8s-finder\nvisibility: team\n---\n", encoding="utf-8")
            (skills / "billing-labeler").mkdir()
            (skills / "billing-labeler" / "SKILL.md").write_text(
                "---\nname: billing-labeler\nvisibility: private\n---\n",
                encoding="utf-8",
            )
            (state / "registry.yaml").write_text(
                "skills:\n"
                "  k8s-finder:\n"
                "    path: /tmp/old-k8s-finder\n"
                "    visibility: team\n"
                "  stale-skill:\n"
                "    path: /tmp/stale-skill\n"
                "    visibility: private\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["registry", "doctor", "--root", str(root)])

            rendered = output.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("path-mismatch: k8s-finder", rendered)
            self.assertIn("stale-registry-skill: stale-skill", rendered)
            self.assertIn("unregistered-skill: billing-labeler", rendered)

    def test_registry_doctor_command_passes_when_registry_matches_vault(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skill = root / "skills" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: k8s-finder\nvisibility: team\n---\n", encoding="utf-8")
            main(["registry", "build", "--root", str(root)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["registry", "doctor", "--root", str(root)])

            self.assertEqual(exit_code, 0)
            self.assertIn("ok: registry", output.getvalue())

    def test_registry_doctor_command_json_outputs_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skills = root / "skills"
            state = root / "state"
            skills.mkdir(parents=True)
            state.mkdir(parents=True)
            current = skills / "k8s-finder"
            current.mkdir()
            (current / "SKILL.md").write_text("---\nname: k8s-finder\nvisibility: team\n---\n", encoding="utf-8")
            (state / "registry.yaml").write_text(
                "skills:\n"
                "  k8s-finder:\n"
                "    path: /tmp/old-k8s-finder\n"
                "    visibility: team\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["registry", "doctor", "--root", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["ok"])
            self.assertIn("path-mismatch: k8s-finder", payload["issues"][0])

    def test_registry_doctor_command_rebuilds_registry_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skills = root / "skills"
            state = root / "state"
            skills.mkdir(parents=True)
            state.mkdir(parents=True)
            current = skills / "k8s-finder"
            current.mkdir()
            (current / "SKILL.md").write_text("---\nname: k8s-finder\nvisibility: team\n---\n", encoding="utf-8")
            registry = state / "registry.yaml"
            registry.write_text(
                "skills:\n"
                "  k8s-finder:\n"
                "    path: /tmp/old-k8s-finder\n"
                "    visibility: team\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["registry", "doctor", "--root", str(root), "--rebuild-if-drift"])

            self.assertEqual(exit_code, 0)
            self.assertIn("rebuilt:", output.getvalue())
            self.assertIn(str(current), registry.read_text(encoding="utf-8"))

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

    def test_ls_command_json_outputs_registry_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            skill = root / "skills" / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: k8s-finder\nvisibility: team\ndescription: Find Kubernetes services\n---\n",
                encoding="utf-8",
            )
            main(["registry", "build", "--root", str(root)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["ls", "--root", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["skills"][0]["name"], "k8s-finder")

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

    def test_find_command_json_outputs_matching_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            finder = root / "skills" / "k8s-finder"
            other = root / "skills" / "billing-labeler"
            finder.mkdir(parents=True)
            other.mkdir(parents=True)
            (finder / "SKILL.md").write_text(
                "---\nname: k8s-finder\ndescription: Find Kubernetes services\nvisibility: team\n---\n",
                encoding="utf-8",
            )
            (other / "SKILL.md").write_text(
                "---\nname: billing-labeler\ndescription: Label billing rows\nvisibility: private\n---\n",
                encoding="utf-8",
            )
            main(["registry", "build", "--root", str(root)])
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["find", "--root", str(root), "--query", "kubernetes", "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual([entry["name"] for entry in payload["skills"]], ["k8s-finder"])

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

    def test_profile_add_command_refuses_to_overwrite_existing_profile(self):
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
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("exists:", output.getvalue())

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

    def test_profile_clone_command_creates_new_profile_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "exclude:\n"
                "  - experimental-*\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile",
                        "clone",
                        "--root",
                        str(root),
                        "--name",
                        "default",
                        "--to",
                        "staging",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (profiles / "staging.yaml").read_text(encoding="utf-8"),
                "name: staging\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "exclude:\n"
                "  - experimental-*\n",
            )
            self.assertTrue((profiles / "default.yaml").exists())
            self.assertIn("cloned:", output.getvalue())

    def test_profile_clone_command_refuses_to_overwrite_existing_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n",
                encoding="utf-8",
            )
            (profiles / "staging.yaml").write_text(
                "name: staging\nagent: codex\nskills:\n  - billing-labeler\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile",
                        "clone",
                        "--root",
                        str(root),
                        "--name",
                        "default",
                        "--to",
                        "staging",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("exists:", output.getvalue())

    def test_profile_rename_command_moves_profile_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile",
                        "rename",
                        "--root",
                        str(root),
                        "--name",
                        "default",
                        "--to",
                        "staging",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertFalse((profiles / "default.yaml").exists())
            self.assertEqual(
                (profiles / "staging.yaml").read_text(encoding="utf-8"),
                "name: staging\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n",
            )
            self.assertIn("renamed:", output.getvalue())

    def test_profile_rename_command_refuses_to_overwrite_existing_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            profiles.mkdir(parents=True)
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n",
                encoding="utf-8",
            )
            (profiles / "staging.yaml").write_text(
                "name: staging\nagent: codex\nskills:\n  - billing-labeler\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile",
                        "rename",
                        "--root",
                        str(root),
                        "--name",
                        "default",
                        "--to",
                        "staging",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("exists:", output.getvalue())

    def test_profile_validate_command_reports_profile_issues(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            skills = root / "skills"
            profiles.mkdir(parents=True)
            skills.mkdir(parents=True)
            (skills / "k8s-finder").mkdir()
            (skills / "k8s-finder" / "SKILL.md").write_text("# skill", encoding="utf-8")
            (profiles / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - k8s-finder\n"
                "  - missing-skill\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "validate", "--root", str(root), "--name", "default"])

            rendered = output.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertIn("profile: default", rendered)
            self.assertIn("duplicate-skill: k8s-finder", rendered)
            self.assertIn("missing-skill: missing-skill", rendered)

    def test_profile_validate_command_passes_clean_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            skills = root / "skills"
            profiles.mkdir(parents=True)
            skills.mkdir(parents=True)
            (skills / "k8s-finder").mkdir()
            (skills / "k8s-finder" / "SKILL.md").write_text("# skill", encoding="utf-8")
            (profiles / "default.yaml").write_text(
                "name: default\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "validate", "--root", str(root), "--name", "default"])

            self.assertEqual(exit_code, 0)
            self.assertIn("ok: default", output.getvalue())

    def test_profile_validate_command_json_outputs_machine_readable_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            profiles = root / "profiles"
            skills = root / "skills"
            profiles.mkdir(parents=True)
            skills.mkdir(parents=True)
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
                exit_code = main(["profile", "validate", "--root", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["profiles"][0]["profile"], "default")
            self.assertFalse(payload["profiles"][0]["valid"])
            self.assertIn("missing-skill: missing-skill", payload["profiles"][0]["issues"])

    def test_audit_command_json_outputs_machine_readable_result(self):
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
                exit_code = main(["audit", "--root", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["profiles"][0]["profile"], "default")
            self.assertEqual(payload["profiles"][0]["missing_skills"], ["missing-skill"])

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
