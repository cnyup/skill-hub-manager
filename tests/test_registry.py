import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.registry import write_registry


class RegistryTests(unittest.TestCase):
    def test_write_registry_writes_scanned_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "skills"
            skill = vault / "k8s-finder"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("# skill", encoding="utf-8")
            output = root / "state" / "registry.yaml"

            write_registry(vault, output)

            content = output.read_text(encoding="utf-8")
            self.assertIn("skills:", content)
            self.assertIn("k8s-finder:", content)
            self.assertIn(str(skill), content)
