import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills" / "skill-installer" / "scripts" / "install_skill.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("skill_installer_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SkillInstallerScriptTests(unittest.TestCase):
    def test_parse_source_github_tree_records_branch_checkout_and_import_path(self):
        module = load_script_module()
        workspace = Path("/tmp/workspace")

        resolved = module.parse_source(
            "https://github.com/example-org/example-repo/tree/release/skills/web-access",
            workspace,
            None,
        )

        self.assertEqual(resolved.mode, "github-tree")
        self.assertEqual(resolved.repo_url, "https://github.com/example-org/example-repo.git")
        self.assertEqual(resolved.git_ref, "release")
        self.assertEqual(
            resolved.checkout_root,
            workspace / "sources" / module.slugify_repo("example-org/example-repo@release"),
        )
        self.assertEqual(
            resolved.import_source,
            resolved.checkout_root / "skills" / "web-access",
        )

    def test_parse_source_github_tree_with_explicit_ref_supports_slash_branch_names(self):
        module = load_script_module()
        workspace = Path("/tmp/workspace")

        resolved = module.parse_source(
            "https://github.com/example-org/example-repo/tree/feature/demo/skills/web-access",
            workspace,
            None,
            git_ref="feature/demo",
        )

        self.assertEqual(resolved.mode, "github-tree")
        self.assertEqual(resolved.git_ref, "feature/demo")
        self.assertEqual(resolved.import_subpath, "skills/web-access")
        self.assertEqual(
            resolved.import_source,
            resolved.checkout_root / "skills" / "web-access",
        )

    def test_parse_source_git_repo_supports_explicit_ref_and_subpath(self):
        module = load_script_module()
        workspace = Path("/tmp/workspace")

        resolved = module.parse_source(
            "file:///tmp/example.git",
            workspace,
            None,
            git_ref="feature/demo",
            source_subpath="custom/skill-dir",
        )

        self.assertEqual(resolved.mode, "git-repo")
        self.assertEqual(resolved.git_ref, "feature/demo")
        self.assertEqual(resolved.import_subpath, "custom/skill-dir")
        self.assertEqual(
            resolved.import_source,
            resolved.checkout_root / "custom/skill-dir",
        )

    def test_parse_source_accepts_file_git_url_without_git_suffix(self):
        module = load_script_module()

        resolved = module.parse_source(
            "file:///tmp/example-repository",
            Path("/tmp/workspace"),
            "web-access",
        )

        self.assertEqual(resolved.mode, "git-repo")
        self.assertEqual(resolved.repo_url, "file:///tmp/example-repository")
        self.assertEqual(resolved.import_source, resolved.checkout_root / "skills" / "web-access")

    def test_parse_source_rejects_parent_directory_subpath(self):
        module = load_script_module()

        with self.assertRaisesRegex(ValueError, "source subpath"):
            module.parse_source(
                "file:///tmp/example.git",
                Path("/tmp/workspace"),
                None,
                source_subpath="../outside",
            )

    def test_detect_single_skill_root_accepts_repo_root_skill(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "SKILL.md").write_text("---\nname: root-skill\n---\n", encoding="utf-8")

            detected = module.detect_single_skill_root(repo)

        self.assertEqual(detected, repo)

    def test_detect_single_skill_root_accepts_single_skill_in_skills_directory(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            skill = repo / "skills" / "web-access"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: web-access\n---\n", encoding="utf-8")

            detected = module.detect_single_skill_root(repo)

        self.assertEqual(detected, skill)

    def test_ensure_remote_checkout_uses_branch_clone_when_ref_is_present(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "repo"
            calls = []

            def fake_run(command, check=True, capture_output=False, text=False):
                calls.append(command)
                if command[:2] == ["git", "clone"]:
                    checkout.mkdir(parents=True, exist_ok=True)
                    (checkout / ".git").mkdir()
                return mock.Mock(returncode=0, stdout="")

            with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
                module.ensure_remote_checkout(
                    "https://github.com/example/repo.git",
                    checkout,
                    update=False,
                    git_ref="release",
                )

        self.assertEqual(
            calls[0],
            [
                "git",
                "clone",
                "--branch",
                "release",
                "--single-branch",
                "https://github.com/example/repo.git",
                str(checkout),
            ],
        )

    def test_ensure_remote_checkout_rejects_origin_mismatch(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "repo"
            checkout.mkdir()
            (checkout / ".git").mkdir()

            def fake_run(command, check=False, capture_output=False, text=False):
                if command[:5] == ["git", "-C", str(checkout), "remote", "get-url"]:
                    return mock.Mock(returncode=0, stdout="https://github.com/other/repo.git\n")
                return mock.Mock(returncode=0, stdout="")

            with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, "origin mismatch"):
                    module.ensure_remote_checkout(
                        "https://github.com/example/repo.git",
                        checkout,
                        update=False,
                    )

    def test_ensure_remote_checkout_accepts_same_repo_with_ssh_origin(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "repo"
            checkout.mkdir()
            (checkout / ".git").mkdir()

            def fake_run(command, check=False, capture_output=False, text=False):
                if command[:5] == ["git", "-C", str(checkout), "remote", "get-url"]:
                    return mock.Mock(returncode=0, stdout="git@github.com:example/repo.git\n")
                return mock.Mock(returncode=0, stdout="")

            with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
                module.ensure_remote_checkout(
                    "https://github.com/example/repo.git",
                    checkout,
                    update=False,
                )

    def test_ensure_remote_checkout_accepts_same_repo_with_ssh_scheme_origin(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "repo"
            checkout.mkdir()
            (checkout / ".git").mkdir()

            def fake_run(command, check=False, capture_output=False, text=False):
                if command[:5] == ["git", "-C", str(checkout), "remote", "get-url"]:
                    return mock.Mock(returncode=0, stdout="ssh://git@github.com/example/repo.git\n")
                return mock.Mock(returncode=0, stdout="")

            with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
                module.ensure_remote_checkout(
                    "https://github.com/example/repo.git",
                    checkout,
                    update=False,
                )

    def test_determine_import_source_requires_existing_explicit_subpath(self):
        module = load_script_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir) / "repo"
            checkout.mkdir()
            resolved = module.ResolvedSource(
                mode="git-repo",
                import_source=checkout / "missing" / "skill",
                repo_url="file:///tmp/example.git",
                checkout_root=checkout,
                git_ref=None,
                import_subpath="missing/skill",
            )

            with self.assertRaisesRegex(ValueError, "does not exist"):
                module.determine_import_source(resolved)

    def test_plan_only_does_not_checkout_remote_source(self):
        module = load_script_module()
        workspace = Path("/tmp/workspace")
        calls = []

        def fake_run(command, check=True, capture_output=False, text=False):
            calls.append(command)
            return mock.Mock(returncode=0, stdout="")

        with mock.patch.object(module.subprocess, "run", side_effect=fake_run):
            exit_code = module.main(
                [
                    "--source",
                    "https://github.com/example-org/example-repo/tree/main/skills/web-access",
                    "--workspace-root",
                    str(workspace),
                    "--plan-only",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(calls, [])
