import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.profiles import (
    Profile,
    clone_profile,
    list_profiles,
    load_profile,
    render_profile_validation_json,
    remove_profile,
    rename_profile,
    update_profile,
    validate_profile,
    write_profile,
)


class ProfileTests(unittest.TestCase):
    def test_load_profile_reads_name_agent_and_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project-a.yaml"
            path.write_text(
                "name: project-a\nagent: codex\nskills:\n  - k8s-finder\n",
                encoding="utf-8",
            )

            profile = load_profile(path)

        self.assertEqual(profile.name, "project-a")
        self.assertEqual(profile.agent, "codex")
        self.assertEqual(profile.skills, ["k8s-finder"])

    def test_load_profile_reads_exclude_and_filters_effective_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project-a.yaml"
            path.write_text(
                "name: project-a\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - billing-labeler\n"
                "exclude:\n"
                "  - billing-labeler\n",
                encoding="utf-8",
            )

            profile = load_profile(path)

        self.assertEqual(profile.exclude, ["billing-labeler"])
        self.assertEqual(profile.effective_skills(), ["k8s-finder"])

    def test_effective_skills_supports_simple_glob_excludes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project-a.yaml"
            path.write_text(
                "name: project-a\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - experimental-k8s\n"
                "  - experimental-feishu\n"
                "exclude:\n"
                "  - experimental-*\n",
                encoding="utf-8",
            )

            profile = load_profile(path)

        self.assertEqual(profile.effective_skills(), ["k8s-finder"])

    def test_list_profiles_returns_sorted_yaml_profiles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            (profiles_dir / "zebra.yaml").write_text("name: zebra\nagent: codex\nskills:\n", encoding="utf-8")
            (profiles_dir / "alpha.yaml").write_text("name: alpha\nagent: codex\nskills:\n", encoding="utf-8")
            (profiles_dir / "notes.txt").write_text("ignore", encoding="utf-8")

            profiles = list_profiles(profiles_dir)

        self.assertEqual([path.name for path in profiles], ["alpha.yaml", "zebra.yaml"])

    def test_write_profile_persists_deterministic_yaml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)

            path = write_profile(
                profiles_dir,
                load_profile(
                    _write_fixture(
                        profiles_dir / "input.yaml",
                        "name: default\n"
                        "agent: codex\n"
                        "skills:\n"
                        "  - billing-labeler\n"
                        "  - k8s-finder\n"
                        "exclude:\n"
                        "  - experimental-*\n",
                    )
                ),
            )

            self.assertEqual(path, profiles_dir / "default.yaml")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - billing-labeler\n"
                "  - k8s-finder\n"
                "exclude:\n"
                "  - experimental-*\n",
            )

    def test_write_profile_refuses_to_overwrite_existing_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            (profiles_dir / "default.yaml").write_text("name: default\nagent: codex\nskills:\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_profile(
                    profiles_dir,
                    Profile(name="default", agent="codex", skills=["k8s-finder"]),
                )

    def test_remove_profile_deletes_existing_profile_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            path = profiles_dir / "default.yaml"
            path.write_text("name: default\nagent: codex\nskills:\n", encoding="utf-8")

            removed = remove_profile(profiles_dir, "default")

        self.assertTrue(removed)
        self.assertFalse(path.exists())

    def test_update_profile_applies_agent_skill_and_exclude_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = load_profile(
                _write_fixture(
                    Path(temp_dir) / "default.yaml",
                    "name: default\n"
                    "agent: codex\n"
                    "skills:\n"
                    "  - k8s-finder\n"
                    "  - billing-labeler\n"
                    "exclude:\n"
                    "  - experimental-*\n",
                )
            )

            updated = update_profile(
                profile,
                agent="claude",
                add_skills=["release-checker", "k8s-finder"],
                remove_skills=["billing-labeler"],
                add_exclude=["legacy-*"],
                remove_exclude=["experimental-*"],
            )

        self.assertEqual(updated.agent, "claude")
        self.assertEqual(updated.skills, ["k8s-finder", "release-checker"])
        self.assertEqual(updated.exclude, ["legacy-*"])

    def test_clone_profile_copies_content_with_new_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            write_profile(
                profiles_dir,
                Profile(
                    name="default",
                    agent="codex",
                    skills=["k8s-finder"],
                    exclude=["experimental-*"],
                ),
            )

            path = clone_profile(profiles_dir, "default", "staging")

            self.assertEqual(path, profiles_dir / "staging.yaml")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "name: staging\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "exclude:\n"
                "  - experimental-*\n",
            )

    def test_clone_profile_refuses_to_overwrite_existing_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            write_profile(
                profiles_dir,
                Profile(name="default", agent="codex", skills=["k8s-finder"]),
            )
            (profiles_dir / "staging.yaml").write_text("name: staging\nagent: codex\nskills:\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                clone_profile(profiles_dir, "default", "staging")

    def test_rename_profile_moves_file_and_updates_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            write_profile(
                profiles_dir,
                Profile(
                    name="default",
                    agent="codex",
                    skills=["k8s-finder"],
                ),
            )

            path = rename_profile(profiles_dir, "default", "staging")

            self.assertEqual(path, profiles_dir / "staging.yaml")
            self.assertFalse((profiles_dir / "default.yaml").exists())
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "name: staging\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n",
            )

    def test_rename_profile_refuses_to_overwrite_existing_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_dir = Path(temp_dir)
            write_profile(
                profiles_dir,
                Profile(name="default", agent="codex", skills=["k8s-finder"]),
            )
            (profiles_dir / "staging.yaml").write_text("name: staging\nagent: codex\nskills:\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                rename_profile(profiles_dir, "default", "staging")

    def test_validate_profile_reports_empty_duplicate_and_missing_skill_issues(self):
        issues = validate_profile(
            Profile(
                name="default",
                agent="codex",
                skills=["k8s-finder", "k8s-finder", "missing-skill"],
            ),
            {"k8s-finder"},
        )

        self.assertEqual(issues, ["duplicate-skill: k8s-finder", "missing-skill: missing-skill"])

    def test_validate_profile_reports_empty_skill_list(self):
        issues = validate_profile(Profile(name="default", agent="codex", skills=[]), set())

        self.assertEqual(issues, ["empty-skills"])

    def test_render_profile_validation_json_returns_stable_payload(self):
        rendered = render_profile_validation_json(
            [
                {"profile": "default", "valid": False, "issues": ["duplicate-skill: k8s-finder"]},
                {"profile": "staging", "valid": True, "issues": []},
            ]
        )

        self.assertEqual(
            rendered,
            '{\n'
            '  "profiles": [\n'
            '    {\n'
            '      "profile": "default",\n'
            '      "valid": false,\n'
            '      "issues": [\n'
            '        "duplicate-skill: k8s-finder"\n'
            '      ]\n'
            '    },\n'
            '    {\n'
            '      "profile": "staging",\n'
            '      "valid": true,\n'
            '      "issues": []\n'
            '    }\n'
            '  ]\n'
            '}',
        )


def _write_fixture(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
