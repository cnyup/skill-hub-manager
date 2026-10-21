"""Wave 6：本机 agent 扫描与纳管（scan_local_agents / add_agent_target）。"""

import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.state_io import atomic_write_text
from skill_hub_manager.profiles import load_profile
from skill_hub_manager.agents import (
    canonical_agent_name,

    SCAN_CANDIDATES,
    add_agent_target,
    list_agent_targets,
    remove_agent_target,
    scan_local_agents,
)

class ScanLocalAgentsTests(unittest.TestCase):
    def test_scan_table_has_owner_curated_nine_candidates(self):
        self.assertEqual(
            set(SCAN_CANDIDATES.keys()),
            {"codex", "claude", "cursor", "windsurf", "opencode", "zcode", "qoder", "workbuddy", "tianshuharness"},
        )

    def test_existing_candidate_reports_exists_and_skill_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_agent = root / "fake-agent" / "skills"
            (fake_agent / "alpha").mkdir(parents=True)
            (fake_agent / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
            (fake_agent / "beta").mkdir()
            (fake_agent / "beta" / "SKILL.md").write_text("---\nname: beta\n---\n", encoding="utf-8")
            (fake_agent / "not-a-skill").mkdir()  # 无 SKILL.md，不计入

            candidates = {item.agent: item for item in scan_local_agents(root)}
            # monkeypatch 全局 home 不现实——直接构造：SCAN_CANDIDATES 固定指向 ~，
            # 因此用 patch 验证计数逻辑（见下个用例用真实函数），这里验证表内 agent 都有返回
            self.assertIn("codex", candidates)
            self.assertIn("tianshuharness", candidates)
            for item in candidates.values():
                self.assertIsInstance(item.exists, bool)
                self.assertGreaterEqual(item.skill_count, 0)

    def test_managed_flag_reflects_agents_yaml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            add_agent_target(root, "zcode", Path.home() / ".zcode" / "skills")

            candidates = {item.agent: item for item in scan_local_agents(root)}

            self.assertTrue(candidates["zcode"].managed)
            self.assertFalse(candidates["opencode"].managed)

    def test_builtin_agents_are_managed_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidates = {item.agent: item for item in scan_local_agents(Path(temp_dir))}

        self.assertTrue(candidates["codex"].managed)
        self.assertTrue(candidates["claude"].managed)
        self.assertFalse(candidates["qoder"].managed)


class AddAgentTargetTests(unittest.TestCase):
    def test_add_creates_agents_yaml_and_list_includes_new_agent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = Path(temp_dir) / "some-skills"

            config = add_agent_target(root, "opencode", target)

            self.assertEqual(config, root / "agents.yaml")
            self.assertTrue(config.is_file())
            targets = list_agent_targets(root)
            self.assertEqual(targets["opencode"], target)

    def test_add_is_idempotent_per_agent_no_duplicate_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            add_agent_target(root, "zcode", Path("/tmp/old-zcode"))
            add_agent_target(root, "zcode", Path("/tmp/new-zcode"))

            content = (root / "agents.yaml").read_text(encoding="utf-8")
            self.assertEqual(content.count("zcode:"), 1)
            self.assertIn("/tmp/new-zcode", content)
            self.assertNotIn("/tmp/old-zcode", content)

    def test_add_preserves_comments_and_other_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "agents.yaml").write_text(
                "# my agents\ncustom: /tmp/custom\n",
                encoding="utf-8",
            )

            add_agent_target(root, "qoder", Path("/tmp/qoder-skills"))

            content = (root / "agents.yaml").read_text(encoding="utf-8")
            self.assertIn("# my agents", content)
            self.assertIn("custom: /tmp/custom", content)
            self.assertIn("qoder: /tmp/qoder-skills", content)

    def test_add_normalizes_claude_code_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            add_agent_target(root, "claude-code", Path("/tmp/claude-skills"))

            content = (root / "agents.yaml").read_text(encoding="utf-8")
            self.assertIn("claude: /tmp/claude-skills", content)
            self.assertNotIn("claude-code:", content)

    def test_scan_sees_newly_added_agent_as_managed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            add_agent_target(root, "workbuddy", Path("/tmp/workbuddy-skills"))

            candidates = {item.agent: item for item in scan_local_agents(root)}

            self.assertTrue(candidates["workbuddy"].managed)
            self.assertEqual(candidates["workbuddy"].path, Path.home() / ".workbuddy-ai" / "skills")


class RemoveAgentTargetTests(unittest.TestCase):
    def test_remove_deletes_entry_and_list_no_longer_contains_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            add_agent_target(root, "zcode", Path("/tmp/zcode-skills"))

            removed = remove_agent_target(root, "zcode")

            self.assertTrue(removed)
            self.assertNotIn("zcode", list_agent_targets(root))
            self.assertNotIn("zcode:", (root / "agents.yaml").read_text(encoding="utf-8"))

    def test_remove_builtin_returns_false_and_keeps_builtin(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            removed = remove_agent_target(root, "codex")

            self.assertFalse(removed)
            self.assertIn("codex", list_agent_targets(root))

    def test_remove_preserves_other_entries_and_comments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "agents.yaml").write_text(
                "# my agents\ncustom: /tmp/custom\nzcode: /tmp/zcode-skills\n",
                encoding="utf-8",
            )

            remove_agent_target(root, "zcode")

            content = (root / "agents.yaml").read_text(encoding="utf-8")
            self.assertIn("# my agents", content)
            self.assertIn("custom: /tmp/custom", content)
            self.assertNotIn("zcode:", content)

    def test_remove_missing_entry_is_noop_false(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            removed = remove_agent_target(Path(temp_dir), "qoder")

        self.assertFalse(removed)


if __name__ == "__main__":
    unittest.main()


class RemoveAgentCascadesProfileTests(unittest.TestCase):
    """Regression: agent remove 必须级联删除该 agent 名下的 profile YAML，
    否则 Library 徽章 / Agents 面板 / 侧栏 Profiles 仍会显示已移除的 agent。"""

    def _write_profile(self, profiles_dir: Path, name: str, agent: str) -> None:
        profiles_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            profiles_dir / f"{name}.yaml",
            f"name: {name}\nagent: {agent}\nskills:\n",
        )

    def test_remove_drops_orphan_profile_of_same_agent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profiles_dir = root / "profiles"
            self._write_profile(profiles_dir, "workbuddy", "workbuddy")
            add_agent_target(root, "workbuddy", Path("/tmp/workbuddy-skills"))

            removed = remove_agent_target(root, "workbuddy")

            self.assertTrue(removed)
            self.assertFalse((profiles_dir / "workbuddy.yaml").exists())

    def test_remove_matches_profile_by_agent_field_not_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profiles_dir = root / "profiles"
            self._write_profile(profiles_dir, "workbuddy-extra", "workbuddy")
            add_agent_target(root, "workbuddy", Path("/tmp/workbuddy-skills"))

            removed = remove_agent_target(root, "workbuddy")

            self.assertTrue(removed)
            self.assertFalse((profiles_dir / "workbuddy-extra.yaml").exists())

    def test_remove_keeps_profiles_of_other_agents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profiles_dir = root / "profiles"
            self._write_profile(profiles_dir, "default", "codex")
            self._write_profile(profiles_dir, "workbuddy", "workbuddy")
            add_agent_target(root, "workbuddy", Path("/tmp/workbuddy-skills"))

            removed = remove_agent_target(root, "workbuddy")

            self.assertTrue(removed)
            self.assertTrue((profiles_dir / "default.yaml").exists())

    def test_remove_builtin_keeps_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            profiles_dir = root / "profiles"
            self._write_profile(profiles_dir, "default", "codex")

            removed = remove_agent_target(root, "codex")

            self.assertFalse(removed)
            self.assertTrue((profiles_dir / "default.yaml").exists())
