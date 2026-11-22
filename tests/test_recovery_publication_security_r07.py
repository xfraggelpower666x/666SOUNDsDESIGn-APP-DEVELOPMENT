"""Recovery archives must never publish on feature or PR refs."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"
GUARD = "if: github.event_name == 'push' && github.ref == 'refs/heads/666DEV'"


class RecoveryPublicationSecurityTests(unittest.TestCase):
    def test_archive_generation_is_default_branch_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        build = text.split("- name: Build revision-bound recovery artifact", 1)[1]
        self.assertEqual(GUARD, build.splitlines()[1].strip())

    def test_upload_is_default_branch_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        upload = text.split("- name: Publish revision-bound recovery artifact", 1)[1]
        self.assertEqual(GUARD, upload.splitlines()[1].strip())

    def test_tests_run_without_guard_and_are_not_skipped_on_pr(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        tests = text.split("- name: Run unit tests", 1)[1].split(
            "- name: Verify repository contracts", 1)[0]
        self.assertNotIn("if:", tests)


if __name__ == "__main__":
    unittest.main()
