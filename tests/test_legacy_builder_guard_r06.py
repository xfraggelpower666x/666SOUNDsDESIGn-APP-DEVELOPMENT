"""Legacy plugin builder must not downgrade provider-current v0.2.2."""
import tempfile
import unittest
from pathlib import Path
from plugin.build import build


class LegacyBuilderGuardTests(unittest.TestCase):
    def test_legacy_builder_fails_closed_without_source_read(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "private-original.zip"  # intentionally absent
            destination = Path(temp) / "plugin.zip"
            with self.assertRaisesRegex(RuntimeError, "WRITE_BLOCKED"):
                build(source, destination)
            self.assertFalse(destination.exists())

    def test_explicit_legacy_build_outside_ignored_work_area_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "missing-source.zip"
            destination = Path(temp) / "would-publish-v015.zip"
            with self.assertRaisesRegex(ValueError, "WRITE_BLOCKED"):
                build(source, destination, allow_legacy_v015=True)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
