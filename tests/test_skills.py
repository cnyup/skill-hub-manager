import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.skills import scan_skills


class SkillScannerTests(unittest.TestCase):
    def test_scan_skills_finds_directories_with_skill_md(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            skill_dir = vault / "k8s-finder"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: k8s-finder\n---\n",
                encoding="utf-8",
            )
            (vault / "notes.txt").write_text("ignore", encoding="utf-8")

            skills = scan_skills(vault)

        self.assertEqual(list(skills), ["k8s-finder"])
        self.assertEqual(skills["k8s-finder"].path, skill_dir)

    def test_scan_skills_reads_frontmatter_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            skill_dir = vault / "k8s-finder"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: k8s-finder\n"
                "description: Find Kubernetes services\n"
                "visibility: team\n"
                "agents:\n"
                "  - codex\n"
                "tags:\n"
                "  - infra\n"
                "---\n"
                "# body\n",
                encoding="utf-8",
            )

            skill = scan_skills(vault)["k8s-finder"]

        self.assertEqual(skill.name, "k8s-finder")
        self.assertEqual(skill.description, "Find Kubernetes services")
        self.assertEqual(skill.visibility, "team")
        self.assertEqual(skill.agents, ("codex",))
        self.assertEqual(skill.tags, ("infra",))
