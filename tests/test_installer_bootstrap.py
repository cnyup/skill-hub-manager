import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from skill_hub_manager.installer_bootstrap import ensure_manager_checkout, run_install_flow


class InstallerBootstrapTests(unittest.TestCase):
    def test_existing_non_directory_checkout_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "skill-hub-manager"
            checkout.write_text("not a repo", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exists but is not a directory"):
                ensure_manager_checkout(
                    repo_url="https://github.com/cnyup/skill-hub-manager.git",
                    checkout_dir=checkout,
                    update=False,
                )

    def test_existing_directory_without_cli_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "skill-hub-manager"
            checkout.mkdir()

            with self.assertRaisesRegex(ValueError, "Expected bin/skill-hub to exist"):
                ensure_manager_checkout(
                    repo_url="https://github.com/cnyup/skill-hub-manager.git",
                    checkout_dir=checkout,
                    update=False,
                )

    @patch("subprocess.run")
    def test_clone_manager_when_checkout_is_missing(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "skill-hub-manager"

            def clone_side_effect(command, check):
                self.assertEqual(command, ["git", "clone", "https://github.com/cnyup/skill-hub-manager.git", str(checkout)])
                self.assertTrue(check)
                (checkout / "bin").mkdir(parents=True)
                (checkout / "bin" / "skill-hub").write_text("#!/bin/sh\n", encoding="utf-8")

            run_mock.side_effect = clone_side_effect

            result = ensure_manager_checkout(
                repo_url="https://github.com/cnyup/skill-hub-manager.git",
                checkout_dir=checkout,
                update=False,
            )

        self.assertEqual(result, checkout)
        self.assertEqual(
            run_mock.call_args_list[0].args[0],
            ["git", "clone", "https://github.com/cnyup/skill-hub-manager.git", str(checkout)],
        )

    @patch("subprocess.run")
    def test_install_flow_runs_manager_commands_in_order(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".skill-hub"
            checkout = root / "skill-hub-manager"
            target = root / ".codex" / "skills"
            cli = checkout / "bin" / "skill-hub"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
            run_mock.return_value = CompletedProcess(args=[], returncode=0, stdout="abc123\n")

            run_install_flow(
                repo_url="https://github.com/cnyup/skill-hub-manager.git",
                checkout_dir=checkout,
                workspace_root=workspace,
                profile="codex",
                agent="codex",
                target_dir=target,
                skills=["demo-skill", "extra-skill"],
                update_manager=False,
            )

        profile_path = workspace / "profiles" / "codex.yaml"
        expected = [
            [str(cli), "init", "--root", str(workspace)],
            [str(cli), "registry", "build", "--root", str(workspace)],
            [
                str(cli),
                "profile",
                "add",
                "--root",
                str(workspace),
                "--name",
                "codex",
                "--agent",
                "codex",
                "--skill",
                "demo-skill",
                "--skill",
                "extra-skill",
            ],
            [str(cli), "profile", "validate", "--root", str(workspace), "--name", "codex"],
            [str(cli), "sync", "--root", str(workspace), "--profile", str(profile_path), "--target", str(target)],
            [str(cli), "doctor", "--root", str(workspace)],
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            [
                str(cli),
                "install-state",
                "record",
                "--root",
                str(workspace),
                "--agent",
                "codex",
                "--profile",
                "codex",
                "--target",
                str(target),
                "--manager-path",
                str(checkout),
                "--manager-repo",
                "https://github.com/cnyup/skill-hub-manager.git",
                "--manager-revision",
                "abc123",
                "--detection-confidence",
                "confirmed",
                "--detection-reason",
                "user-confirmed-target",
            ],
        ]
        self.assertEqual([call.args[0] for call in run_mock.call_args_list], expected)

    @patch("subprocess.run")
    def test_install_flow_first_install_creates_profile(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".skill-hub"
            checkout = root / "skill-hub-manager"
            target = root / ".codex" / "skills"
            cli = checkout / "bin" / "skill-hub"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
            run_mock.return_value = CompletedProcess(args=[], returncode=0, stdout="abc123\n")

            run_install_flow(
                repo_url="https://github.com/cnyup/skill-hub-manager.git",
                checkout_dir=checkout,
                workspace_root=workspace,
                profile="codex",
                agent="codex",
                target_dir=target,
                skills=["demo-skill", "extra-skill"],
                update_manager=False,
            )

        commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertIn(
            [
                str(cli),
                "profile",
                "add",
                "--root",
                str(workspace),
                "--name",
                "codex",
                "--agent",
                "codex",
                "--skill",
                "demo-skill",
                "--skill",
                "extra-skill",
            ],
            commands,
        )

    @patch("subprocess.run")
    def test_install_flow_reuses_existing_profile_without_modifying_it_by_default(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".skill-hub"
            checkout = root / "skill-hub-manager"
            target = root / ".codex" / "skills"
            cli = checkout / "bin" / "skill-hub"
            profile_path = workspace / "profiles" / "codex.yaml"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text("name: codex\n", encoding="utf-8")
            run_mock.return_value = CompletedProcess(args=[], returncode=0, stdout="abc123\n")

            run_install_flow(
                repo_url="https://github.com/cnyup/skill-hub-manager.git",
                checkout_dir=checkout,
                workspace_root=workspace,
                profile="codex",
                agent="codex",
                target_dir=target,
                skills=["demo-skill", "extra-skill"],
                update_manager=False,
            )

        commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertNotIn("add", [command[2] for command in commands if command[:2] == [str(cli), "profile"]])
        self.assertNotIn("update", [command[2] for command in commands if command[:2] == [str(cli), "profile"]])
        self.assertIn([str(cli), "profile", "validate", "--root", str(workspace), "--name", "codex"], commands)
        self.assertIn(
            [str(cli), "sync", "--root", str(workspace), "--profile", str(profile_path), "--target", str(target)],
            commands,
        )
        self.assertIn([str(cli), "doctor", "--root", str(workspace)], commands)
        self.assertIn(["git", "-C", str(checkout), "rev-parse", "HEAD"], commands)
        self.assertIn(
            [
                str(cli),
                "install-state",
                "record",
                "--root",
                str(workspace),
                "--agent",
                "codex",
                "--profile",
                "codex",
                "--target",
                str(target),
                "--manager-path",
                str(checkout),
                "--manager-repo",
                "https://github.com/cnyup/skill-hub-manager.git",
                "--manager-revision",
                "abc123",
                "--detection-confidence",
                "confirmed",
                "--detection-reason",
                "user-confirmed-target",
            ],
            commands,
        )

    @patch("subprocess.run")
    def test_install_flow_updates_existing_profile_incrementally_when_enabled(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".skill-hub"
            checkout = root / "skill-hub-manager"
            target = root / ".codex" / "skills"
            cli = checkout / "bin" / "skill-hub"
            profile_path = workspace / "profiles" / "codex.yaml"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text("name: codex\n", encoding="utf-8")
            run_mock.return_value = CompletedProcess(args=[], returncode=0, stdout="abc123\n")

            run_install_flow(
                repo_url="https://github.com/cnyup/skill-hub-manager.git",
                checkout_dir=checkout,
                workspace_root=workspace,
                profile="codex",
                agent="codex",
                target_dir=target,
                skills=["demo-skill", "extra-skill"],
                update_manager=False,
                update_profile_skills=True,
            )

        commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertIn(
            [
                str(cli),
                "profile",
                "update",
                "--root",
                str(workspace),
                "--name",
                "codex",
                "--add-skill",
                "demo-skill",
                "--add-skill",
                "extra-skill",
            ],
            commands,
        )
        self.assertNotIn("add", [command[2] for command in commands if command[:2] == [str(cli), "profile"]])

    @patch("subprocess.run")
    def test_install_flow_with_empty_mode_stops_before_profile_sync_and_record(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".skill-hub"
            checkout = root / "skill-hub-manager"
            target = root / ".codex" / "skills"
            cli = checkout / "bin" / "skill-hub"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")

            run_install_flow(
                repo_url="https://github.com/cnyup/skill-hub-manager.git",
                checkout_dir=checkout,
                workspace_root=workspace,
                profile="codex",
                agent="codex",
                target_dir=target,
                skills=[],
                update_manager=False,
                mode="empty",
            )

        commands = [call.args[0] for call in run_mock.call_args_list]
        self.assertEqual(
            commands,
            [
                [str(cli), "init", "--root", str(workspace)],
                [str(cli), "registry", "build", "--root", str(workspace)],
            ],
        )

    @patch("subprocess.run")
    def test_install_flow_rejects_empty_skills_in_apply_mode(self, run_mock):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / ".skill-hub"
            checkout = root / "skill-hub-manager"
            target = root / ".codex" / "skills"
            cli = checkout / "bin" / "skill-hub"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "skills must be confirmed before validate/sync"):
                run_install_flow(
                    repo_url="https://github.com/cnyup/skill-hub-manager.git",
                    checkout_dir=checkout,
                    workspace_root=workspace,
                    profile="codex",
                    agent="codex",
                    target_dir=target,
                    skills=[],
                    update_manager=False,
                )

        self.assertEqual(run_mock.call_args_list, [])


if __name__ == "__main__":
    unittest.main()
