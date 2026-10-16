"""Regression tests for --json output on profile/registry-build/doctor commands.

These pin the machine-readable contracts consumed by the desktop client
(desktop/src/api/). RED first: the flags do not exist yet (argparse rejects
--json with SystemExit 2), so every test below must fail before the
implementation lands and pass after.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.cli import main


def _make_workspace(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "skills").mkdir(exist_ok=True)
    (root / "profiles").mkdir(exist_ok=True)
    (root / "state").mkdir(exist_ok=True)
    (root / "sources").mkdir(exist_ok=True)
    return root


def _make_skill(root: Path, name: str, description: str = "demo skill") -> None:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    front_matter = (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "---\n"
    )
    (skill_dir / "SKILL.md").write_text(front_matter + f"\n# {name}\n", encoding="utf-8")


class ProfileListJsonTests(unittest.TestCase):
    def test_profile_list_json_outputs_sorted_profile_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            profiles = root / "profiles"
            (profiles / "zebra.yaml").write_text("name: zebra\nagent: codex\nskills:\n", encoding="utf-8")
            (profiles / "alpha.yaml").write_text("name: alpha\nagent: claude\nskills:\n", encoding="utf-8")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "list", "--root", str(root), "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["profiles"], ["alpha", "zebra"])


class ProfileShowJsonTests(unittest.TestCase):
    def test_profile_show_json_outputs_full_profile_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            (root / "profiles" / "default.yaml").write_text(
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
                exit_code = main(["profile", "show", "--root", str(root), "--name", "default", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["profile"],
            {
                "name": "default",
                "agent": "codex",
                "skills": ["k8s-finder", "experimental-k8s"],
                "exclude": ["experimental-*"],
                "effective_skills": ["k8s-finder"],
            },
        )


class ProfileAddJsonTests(unittest.TestCase):
    def test_profile_add_json_outputs_written_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile", "add", "--root", str(root),
                        "--name", "codex", "--agent", "codex",
                        "--skill", "k8s-finder", "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["written"], str(root / "profiles" / "codex.yaml"))
            self.assertTrue(Path(payload["written"]).exists())

    def test_profile_add_json_outputs_error_and_nonzero_on_conflict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            (root / "profiles" / "codex.yaml").write_text(
                "name: codex\nagent: codex\nskills:\n", encoding="utf-8"
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                with contextlib.redirect_stderr(io.StringIO()):
                    exit_code = main(
                        [
                            "profile", "add", "--root", str(root),
                            "--name", "codex", "--agent", "codex",
                            "--skill", "k8s-finder", "--json",
                        ]
                    )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertIn("error", payload)
        self.assertIn("exists", payload["error"])


class ProfileRemoveJsonTests(unittest.TestCase):
    def test_profile_remove_json_outputs_removed_true(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            (root / "profiles" / "old.yaml").write_text(
                "name: old\nagent: codex\nskills:\n", encoding="utf-8"
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "remove", "--root", str(root), "--name", "old", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["removed"])

    def test_profile_remove_json_outputs_removed_false_and_nonzero_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["profile", "remove", "--root", str(root), "--name", "ghost", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["removed"])


class ProfileUpdateJsonTests(unittest.TestCase):
    def test_profile_update_json_outputs_updated_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            (root / "profiles" / "codex.yaml").write_text(
                "name: codex\nagent: codex\nskills:\n  - k8s-finder\n", encoding="utf-8"
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "profile", "update", "--root", str(root), "--name", "codex",
                        "--add-skill", "web-access", "--json",
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["updated"], str(root / "profiles" / "codex.yaml"))
        self.assertEqual(payload["profile"]["skills"], ["k8s-finder", "web-access"])


class ProfileCloneRenameJsonTests(unittest.TestCase):
    def test_profile_clone_json_outputs_cloned_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            (root / "profiles" / "codex.yaml").write_text(
                "name: codex\nagent: codex\nskills:\n  - k8s-finder\n", encoding="utf-8"
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["profile", "clone", "--root", str(root), "--name", "codex", "--to", "codex-copy", "--json"]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["cloned"], str(root / "profiles" / "codex-copy.yaml"))

    def test_profile_rename_json_outputs_renamed_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            (root / "profiles" / "old-name.yaml").write_text(
                "name: old-name\nagent: codex\nskills:\n  - k8s-finder\n", encoding="utf-8"
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["profile", "rename", "--root", str(root), "--name", "old-name", "--to", "new-name", "--json"]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["renamed"], str(root / "profiles" / "new-name.yaml"))
        self.assertFalse((root / "profiles" / "old-name.yaml").exists())


class RegistryBuildJsonTests(unittest.TestCase):
    def test_registry_build_json_outputs_written_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            _make_skill(root, "k8s-finder")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["registry", "build", "--root", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["wrote"], str(root / "state" / "registry.yaml"))
            self.assertTrue(Path(payload["wrote"]).exists())


class DoctorJsonTests(unittest.TestCase):
    def test_doctor_json_outputs_broken_and_expected_missing_lists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _make_workspace(Path(temp_dir) / "workspace")
            target = Path(temp_dir) / "target"
            target.mkdir()
            broken = target / "broken-link"
            broken.symlink_to(target / "does-not-exist")
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["doctor", "--target", str(target), "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["broken"], ["broken-link"])
        self.assertEqual(payload["expected_missing"], [])


if __name__ == "__main__":
    unittest.main()
