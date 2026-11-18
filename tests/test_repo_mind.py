import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub import core, repo_mind


class RepoMindTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.root / "registry").mkdir()
        shutil.copy(core.ROOT / repo_mind.RULES, self.root / repo_mind.RULES)
        self.write(".gitignore", ".work/\n")
        core.git(self.root, "init", "-q", "-b", "main")
        core.git(self.root, "config", "user.email", "test@example.invalid")
        core.git(self.root, "config", "user.name", "666DEV test")

    def write(self, path, content):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")

    def commit(self):
        core.git(self.root, "add", ".")
        core.git(self.root, "commit", "-qm", "test tree")
        return core.git(self.root, "rev-parse", "HEAD")

    def rename_fixture(self):
        self.write("README.md", "[guide](docs/old.md?view=1#title)\n"
                                "[guide-ref]: docs/old.md\n"
                                "```md\n[example](docs/old.md)\n```\n")
        self.write("docs/old.md", "# Title\n\nGuide\n")
        self.write("projects/one/notes.md", "[guide](../../docs/old.md)\n")
        base = self.commit()
        core.git(self.root, "mv", "docs/old.md", "docs/new guide.md")
        head = self.commit()
        return base, head

    def test_structure_index_and_unique_link(self):
        base, head = self.rename_fixture()
        self.write("untracked.md", "local work")
        report, edits = repo_mind.scan(self.root, base)
        self.assertEqual(2, report["eligible_fixes"])
        self.assertTrue(any(f["rule"] == "missing-root" for f in report["findings"]))
        self.assertTrue(any(f["disposition"] == "REVIEW" and f["path"] == "projects/one/notes.md"
                            for f in report["findings"]))
        self.assertEqual({"README.md"}, edits.keys())
        self.assertIn("docs/new%20guide.md?view=1#title", edits["README.md"])
        self.assertIn("[example](docs/old.md)", edits["README.md"])
        report = repo_mind.refresh_index(self.root)
        index = json.loads((self.root / report["path"]).read_bytes())
        self.assertEqual(head, index["commit"])
        self.assertNotIn("untracked.md", [f["path"] for f in index["files"]])
        self.assertIn("docs/old.md", (self.root / "README.md").read_text())
        shutil.copy(self.root / "docs/new guide.md", self.root / "docs/second.md")
        self.commit()
        self.assertEqual({}, repo_mind.scan(self.root, base)[1])

    def test_publish_isolates_commit_and_reuses_verified_branch(self):
        base, head = self.rename_fixture()
        remote = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        core.git(remote, "init", "--bare", "-q")
        core.git(self.root, "remote", "add", "origin", str(remote))
        core.git(self.root, "push", "origin", "main")
        fixed_branch = f"666repo-mind/links-{head[:16]}-{base[:16]}"
        target = f"refs/heads/{fixed_branch}"

        def git(root, *args):
            if args == ("remote", "get-url", "--push", "origin"):
                return f"https://github.com/{repo_mind.REPOSITORY}.git"
            return core.git(root, *args)

        def github(root, *args):
            if args[:2] == ("pr", "list"):
                return "[]"
            self.assertEqual(("pr", "create"), args[:2])
            return "https://github.com/example/fixture/pull/1"

        # Git operates on a real temporary bare repository. Only GitHub is substituted.
        with patch.object(repo_mind, "git", git), patch.object(repo_mind, "gh", side_effect=github) as github_mock:
            self.assertEqual("PR_CREATED", repo_mind.publish(self.root, base, "main")["status"])
            repair = core.git(remote, "rev-parse", target)
            self.assertEqual(head, core.git(remote, "rev-parse", f"{target}^"))
            self.assertEqual("README.md", core.git(remote, "diff", "--name-only", head, repair))
            self.assertIn("docs/new%20guide.md", core.git(remote, "show", f"{repair}:README.md"))
            github_mock.side_effect = None
            github_mock.return_value = json.dumps([{"headRefOid": repair, "url": "https://example.test/pr/1"}])
            self.assertEqual("EXISTING_PR", repo_mind.publish(self.root, base, "main")["status"])
        self.assertEqual(head, core.git(self.root, "rev-parse", "HEAD"))
        self.assertEqual("", core.git(self.root, "status", "--porcelain"))
