"""Tests for atomic_write_text.

Invariant under test: a failed/interrupted write must leave the original file
completely intact (readable, untruncated), because tmp-file content only
becomes visible via os.replace after a full write. This is the concurrency
safety net for desktop-app + CLI writing the same state files.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from skill_hub_manager.state_io import atomic_write_text


class AtomicWriteTextTests(unittest.TestCase):
    def test_writes_new_file_and_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "dir" / "file.txt"

            result = atomic_write_text(target, "hello")

            self.assertEqual(result, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "hello")

    def test_replaces_existing_file_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "file.txt"
            target.write_text("old content", encoding="utf-8")

            atomic_write_text(target, "new content")

            self.assertEqual(target.read_text(encoding="utf-8"), "new content")

    def test_interrupted_write_leaves_original_intact(self):
        """RED driver for the atomicity invariant.

        Simulate a crash between tmp write and replace by raising from
        os.replace. With plain write_text the original would already be
        truncated/clobbered; with atomic_write_text it must survive.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.json"
            target.write_text('{"records": ["original"]}', encoding="utf-8")

            real_replace = os.replace

            def exploding_replace(src, dst):
                raise OSError("simulated crash before replace")

            with mock.patch("skill_hub_manager.state_io.os.replace", exploding_replace):
                with self.assertRaises(OSError):
                    atomic_write_text(target, '{"records": ["partial"]}')

            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{"records": ["original"]}',
            )

    def test_no_tmp_files_left_behind_after_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.json"
            target.write_text("original", encoding="utf-8")

            def exploding_replace(src, dst):
                raise OSError("boom")

            with mock.patch("skill_hub_manager.state_io.os.replace", exploding_replace):
                with self.assertRaises(OSError):
                    atomic_write_text(target, "partial")

            leftovers = [p for p in Path(temp_dir).iterdir() if p != target]
            self.assertEqual(leftovers, [])

    def test_write_failure_during_tmp_write_leaves_original_intact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.json"
            target.write_text("original", encoding="utf-8")

            with mock.patch(
                "skill_hub_manager.state_io.Path.write_text",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaises(OSError):
                    atomic_write_text(target, "partial")

            self.assertEqual(target.read_text(encoding="utf-8"), "original")


if __name__ == "__main__":
    unittest.main()
