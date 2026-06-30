import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from skill_hub_manager.installer_bootstrap import ensure_manager_checkout, run_install_flow


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    def test_detect_target_script_prints_json_payload(self):
        script = REPO_ROOT / "skills" / "install-skill-hub" / "scripts" / "detect_target.py"
        module = _load_script_module(script, "detect_target_script")

        with tempfile.TemporaryDirectory() as temp_dir, patch("sys.stdout", new_callable=io.StringIO) as stdout:
            exit_code = module.main([temp_dir, "codex"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["agent"], "codex")
        self.assertTrue(payload["detected"])
        self.assertEqual(payload["confidence"], "medium")
        self.assertEqual(payload["target_dir"], str(Path.home() / ".codex" / "skills"))
        self.assertEqual(payload["reason"], "builtin-agent-mapping")


if __name__ == "__main__":
    unittest.main()
