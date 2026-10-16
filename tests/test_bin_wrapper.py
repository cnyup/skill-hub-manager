"""Integration test for the bin/skill-hub wrapper script.

The wrapper must resolve a Python >=3.11 interpreter before exec'ing the CLI.
Before the probe logic existed it hardcoded `python3`, which crashes with
TypeError on machines whose default python3 is 3.9 (realpath: this repo's
pyproject declares >=3.11 but macOS ships 3.9.6 as /usr/bin/python3).
"""

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WRAPPER = REPO_ROOT / "bin" / "skill-hub"


class BinWrapperTests(unittest.TestCase):
    def test_wrapper_resolves_compatible_python_and_prints_version(self):
        completed = subprocess.run(
            [str(WRAPPER), "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("skill-hub", completed.stdout)

    def test_wrapper_supports_json_flag_end_to_end(self):
        completed = subprocess.run(
            [str(WRAPPER), "agent", "detect", "--root", str(REPO_ROOT), "--agent", "codex", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"agent": "codex"', completed.stdout)


if __name__ == "__main__":
    unittest.main()
