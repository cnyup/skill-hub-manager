import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.registry import build_registry, write_registry


class RegistryTests(unittest.TestCase):
    def test_write_registry_writes_scanned_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "skills"
            skill = vault / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: k8s-finder\n"
                "description: Find Kubernetes services\n"
                "visibility: team\n"
                "agents:\n"
                "  - codex\n"
                "  - claude\n"
                "tags:\n"
                "  - infra\n"
                "  - kubernetes\n"
                "---\n"
                "# skill\n",
                encoding="utf-8",
            )
            output = root / "state" / "registry.yaml"

            write_registry(vault, output)

            content = output.read_text(encoding="utf-8")
            self.assertIn("skills:", content)
            self.assertIn("k8s-finder:", content)
            self.assertIn(str(skill), content)
            self.assertIn("description: Find Kubernetes services", content)
            self.assertIn("visibility: team", content)
            self.assertIn("agents: [codex, claude]", content)
            self.assertIn("tags: [infra, kubernetes]", content)

    def test_build_registry_sorts_skills_and_omits_empty_optional_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "skills"
            zebra = vault / "zebra-skill"
            alpha = vault / "alpha-skill"
            zebra.mkdir(parents=True)
            alpha.mkdir(parents=True)
            (zebra / "SKILL.md").write_text(
                "---\n"
                "name: zebra-skill\n"
                "visibility: private\n"
                "---\n"
                "# skill\n",
                encoding="utf-8",
            )
            (alpha / "SKILL.md").write_text(
                "---\n"
                "name: alpha-skill\n"
                "description: A skill\n"
                "visibility: team\n"
                "---\n"
                "# skill\n",
                encoding="utf-8",
            )

            content = build_registry(vault)

        self.assertLess(content.index("alpha-skill:"), content.index("zebra-skill:"))
        zebra_block = content.split("zebra-skill:", 1)[1]
        self.assertNotIn("description:", zebra_block.split("alpha-skill:", 1)[0] if "alpha-skill:" in zebra_block else zebra_block)
        self.assertNotIn("agents:", zebra_block)
        self.assertNotIn("tags:", zebra_block)
