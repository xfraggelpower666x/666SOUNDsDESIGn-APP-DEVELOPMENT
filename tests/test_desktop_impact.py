import tempfile
import unittest
from pathlib import Path

from devhub import core
from devhub.desktop_impact import desktop_impact


class DesktopImpactTest(unittest.TestCase):
    def test_revision_scope_and_windows_acceptance_are_separate(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        core.git(root, "init", "-q")
        core.git(root, "config", "user.name", "666DEV test")
        core.git(root, "config", "user.email", "test@example.invalid")

        def commit(path):
            file = root / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("example", encoding="utf-8")
            core.git(root, "add", "--", path)
            core.git(root, "commit", "-qm", path)
            return core.git(root, "rev-parse", "HEAD")

        initial = commit("README.md")
        self.assertEqual("READBACK_PENDING", desktop_impact(root, initial)["status"])
        docs = commit("docs/notes.md")
        self.assertEqual("NO_IMPACT_IN_DIFF", desktop_impact(root, docs)["status"])
        live = commit("src/devhub/repo_mind.py")
        finding = desktop_impact(root, live)
        self.assertEqual(docs, finding["base"])
        self.assertEqual("WINDOWS_REVIEW_REQUIRED", finding["status"])
        self.assertEqual("Repo-Mind-Ansicht und Freigabe", finding["live_changes"][0]["area"])
        self.assertEqual([], finding["desktop_changes"])
        pc = commit("windows-app/ui/app.js")
        result = desktop_impact(root, pc, initial)
        self.assertEqual("WINDOWS_REVIEW_REQUIRED", result["status"])
        self.assertEqual(["windows-app/ui/app.js"], result["desktop_changes"])
        self.assertEqual("OFFEN", result["windows_acceptance"])
        self.assertEqual("READBACK_PENDING", desktop_impact(root, docs, pc)["status"])
