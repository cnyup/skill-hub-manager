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

    def test_scan_skills_reads_multiline_description_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            skill_dir = vault / "k8s-finder"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: k8s-finder\n"
                "description: |\n"
                "  Find Kubernetes business services by IP addresses.\n"
                "  Search ConfigMaps by keyword across clusters.\n"
                "visibility: team\n"
                "---\n"
                "# body\n",
                encoding="utf-8",
            )

            skill = scan_skills(vault)["k8s-finder"]

        self.assertEqual(
            skill.description,
            "Find Kubernetes business services by IP addresses.\n"
            "Search ConfigMaps by keyword across clusters.",
        )
        self.assertEqual(skill.visibility, "team")

    def test_scan_skills_reads_multiline_description_with_blank_lines_and_bullets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            skill_dir = vault / "k8s-finder"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: k8s-finder\n"
                "description: |\n"
                "  Find Kubernetes business services by IP addresses.\n"
                "  \n"
                "  **Use this skill whenever the user:**\n"
                "  - Has a list of IPs and needs to find which services own them\n"
                "  - Wants to find ConfigMaps by keyword\n"
                "visibility: team\n"
                "---\n"
                "# body\n",
                encoding="utf-8",
            )

            skill = scan_skills(vault)["k8s-finder"]

        self.assertEqual(
            skill.description,
            "Find Kubernetes business services by IP addresses.\n"
            "\n"
            "**Use this skill whenever the user:**\n"
            "- Has a list of IPs and needs to find which services own them\n"
            "- Wants to find ConfigMaps by keyword",
        )

    def test_scan_skills_reads_indented_multiline_description_without_pipe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            skill_dir = vault / "web-access"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: web-access\n"
                "license: MIT\n"
                "description:\n"
                "  所有联网操作必须通过此 skill 处理。\n"
                "  触发场景：用户要求搜索信息、查看网页内容。\n"
                "metadata:\n"
                "  author: tester\n"
                "  version: \"1.0.0\"\n"
                "---\n"
                "# body\n",
                encoding="utf-8",
            )

            skill = scan_skills(vault)["web-access"]

        self.assertEqual(
            skill.description,
            "所有联网操作必须通过此 skill 处理。\n"
            "触发场景：用户要求搜索信息、查看网页内容。",
        )
