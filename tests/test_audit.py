import tempfile
import unittest
from pathlib import Path

from skill_hub_manager.audit import audit_profiles


class AuditTests(unittest.TestCase):
    def test_audit_profiles_reports_effective_and_missing_skills(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skills_dir = root / "skills"
            profiles_dir = root / "profiles"
            skills_dir.mkdir()
            profiles_dir.mkdir()
            (skills_dir / "k8s-finder").mkdir()
            (skills_dir / "k8s-finder" / "SKILL.md").write_text("# skill", encoding="utf-8")
            (profiles_dir / "default.yaml").write_text(
                "name: default\n"
                "agent: codex\n"
                "skills:\n"
                "  - k8s-finder\n"
                "  - missing-skill\n",
                encoding="utf-8",
            )

            reports = audit_profiles(profiles_dir, skills_dir)

        self.assertEqual(len(reports), 1)
        report = reports[0]
        self.assertEqual(report["profile"], "default")
        self.assertEqual(report["agent"], "codex")
        self.assertEqual(report["effective_skills"], ["k8s-finder", "missing-skill"])
        self.assertEqual(report["missing_skills"], ["missing-skill"])
