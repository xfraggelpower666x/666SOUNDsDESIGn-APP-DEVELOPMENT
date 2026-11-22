"""Private plugin payload names are excluded before any public release."""
import unittest
from devhub.intelligence.publication_safety import forbidden_tracked_paths


class PublicationSafetyTests(unittest.TestCase):
    def test_known_private_snapshot_directories_blocked(self):
        values = [
            ".github/references/coding-profi-v087-source/skills/foo/SKILL.md",
            ".github/coding-control-plugin-snapshot/plugin.json",
            "safe/docs/overview.md",
        ]
        self.assertEqual(values[:2], forbidden_tracked_paths(values))

    def test_windows_separators_and_case_cannot_bypass(self):
        values = [r".github\CODING-CONTROL-PLUGIN-SNAPSHOT\plugin.json"]
        self.assertEqual(values, forbidden_tracked_paths(values))

    def test_private_zip_filename_blocked_but_normal_repo_paths_preserved(self):
        self.assertEqual(["incoming/666dev-coding-control.zip"],
                         forbidden_tracked_paths(["src/devhub/cli.py", "incoming/666dev-coding-control.zip"]))
        self.assertEqual([], forbidden_tracked_paths([
            "plugin/build.py", "plugin/README.md", "src/devhub/intelligence/coding_profi.py",
            ".github/skills/666dev-livecircle/SKILL.md",
        ]))


if __name__ == "__main__":
    unittest.main()
