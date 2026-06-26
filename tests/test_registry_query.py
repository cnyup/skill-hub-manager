import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.registry import find_registry_entries, load_registry_entries, write_registry


class RegistryQueryTests(unittest.TestCase):
    def test_load_registry_entries_reads_sorted_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            vault = root / "skills"
            alpha = vault / "alpha-skill"
            zebra = vault / "zebra-skill"
            alpha.mkdir(parents=True)
            zebra.mkdir(parents=True)
            (alpha / "SKILL.md").write_text(
                "---\nname: alpha-skill\ndescription: Alpha tool\nvisibility: team\n---\n",
                encoding="utf-8",
            )
            (zebra / "SKILL.md").write_text(
                "---\nname: zebra-skill\nvisibility: private\n---\n",
                encoding="utf-8",
            )
            registry = root / "state" / "registry.yaml"
            write_registry(vault, registry)

            entries = load_registry_entries(registry)

        self.assertEqual([entry["name"] for entry in entries], ["alpha-skill", "zebra-skill"])

    def test_find_registry_entries_matches_name_description_and_tags(self):
        entries = [
            {
                "name": "k8s-finder",
                "path": "/tmp/k8s-finder",
                "visibility": "team",
                "description": "Find Kubernetes services",
                "agents": ["codex"],
                "tags": ["infra", "kubernetes"],
            },
            {
                "name": "billing-labeler",
                "path": "/tmp/billing-labeler",
                "visibility": "private",
                "description": "Label billing rows",
                "agents": ["claude"],
                "tags": ["finance"],
            },
        ]

        matches = find_registry_entries(entries, "kubernetes")

        self.assertEqual([entry["name"] for entry in matches], ["k8s-finder"])
