"""R10 native GitHub draft transport: explicit-only, zero-cost and CAS-gated."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub.core import DevhubError
from devhub.intelligence import codeforge_publication as publication

HEAD = "b" * 40
NEW = "c" * 40
RID = "a" * 24
PROJECT = "r10demo"


class DraftPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp) / "repo"
        self.root.mkdir()
        self.work = Path(self.tmp) / ".work"
        self.worktree = self.work / "worktrees" / PROJECT / "safe"
        file = self.worktree / "app/src/file.py"
        file.parent.mkdir(parents=True)
        file.write_text("print('safe')\n", encoding="utf-8")
        self.receipt_path = self.work / "codeforge-receipts" / PROJECT / (RID + ".json")
        self.receipt_path.parent.mkdir(parents=True)
        self.receipt = {
            "schema": "666dev-codeforge-execution/v1",
            "authority": "666DEV", "receipt_id": RID, "project_id": PROJECT,
            "source_commit": HEAD, "worktree": str(self.worktree),
            "isolated_patch_applied": True, "readback_verified": True,
            "remote_peer_executed": False, "github_write_verified": False,
            "current_updated": False,
            "changed_file_sha256": {
                "src/file.py": hashlib.sha256(file.read_bytes()).hexdigest()
            },
        }
        self.save()
        self.enterContext(patch.object(publication, "ROOT", self.root))
        self.enterContext(patch.object(publication, "WORK", self.work))
        self.enterContext(patch("devhub.core.project_profile", return_value=(
            {"id": PROJECT, "source_mode": "monorepo", "source_path": "app"}, Path(self.tmp)
        )))

    def save(self):
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")

    def publish(self, **changes):
        args = {"project_id": PROJECT, "receipt_id": RID, "expected_head": HEAD,
                "target_branch": "main", "confirmation": "CONFIRM_DRAFT_PR"}
        args.update(changes)
        return publication.publish_draft(**args)

    def test_refuses_unconfirmed_publication_before_any_git_call(self):
        with patch.object(publication, "git") as git:
            with self.assertRaisesRegex(DevhubError, "confirmation"):
                self.publish(confirmation="NOT_AUTHORIZED")
            git.assert_not_called()

    def test_stale_head_rejected_before_any_git_call(self):
        with patch.object(publication, "git") as git:
            with self.assertRaisesRegex(DevhubError, "integrity"):
                self.publish(expected_head="d" * 40)
            git.assert_not_called()

    def test_external_owner_cannot_be_promoted(self):
        self.receipt["authority"] = "666CLIC"
        self.save()
        with patch.object(publication, "git") as git:
            with self.assertRaisesRegex(DevhubError, "native ownership"):
                self.publish()
            git.assert_not_called()

    def test_changed_file_hash_rejected_before_network(self):
        file = self.worktree / "app/src/file.py"
        file.write_text("tampered\n", encoding="utf-8")
        with patch.object(publication, "gh") as gh:
            with self.assertRaisesRegex(DevhubError, "changed since"):
                self.publish()
            gh.assert_not_called()

    def test_linked_foreign_project_refused(self):
        with patch("devhub.core.project_profile", return_value=(
            {"id": PROJECT, "source_mode": "linked", "source_path": "app"}, Path(self.tmp)
        )):
            with patch.object(publication, "gh") as gh:
                with self.assertRaisesRegex(DevhubError, "cross-repository"):
                    self.publish()
                gh.assert_not_called()

    def test_private_github_repo_blocked_before_push(self):
        def git(_, *args):
            if args == ("rev-parse", "HEAD"):
                return HEAD
            if args == ("remote", "get-url", "--push", "origin"):
                return "https://github.com/xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT.git"
            if args[:2] == ("ls-remote", "--refs"):
                return HEAD + "\trefs/heads/main"
            raise AssertionError(args)
        with patch.object(publication, "git", side_effect=git) as mock_git:
            with patch.object(publication, "gh", return_value='{"isPrivate":true}'):
                with self.assertRaisesRegex(DevhubError, "zero additional cost"):
                    self.publish()
            self.assertFalse(any("push" in args for _, args, _ in (
                (c.args[0], c.args[1:], c.kwargs) for c in mock_git.call_args_list)))

    def test_confirmed_public_draft_pr_has_remote_readback_without_merge(self):
        calls = []
        def git(root, *args):
            calls.append(args)
            if args == ("rev-parse", "HEAD"):
                return NEW if root == self.worktree and ("commit",) in calls else HEAD
            if args == ("remote", "get-url", "--push", "origin"):
                return "https://github.com/xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT.git"
            if args[:2] == ("ls-remote", "--refs"):
                ref = args[-1]
                if ref == "refs/heads/main":
                    return HEAD + "\t" + ref
                if ref.startswith("refs/heads/666codeforge/r10-"):
                    return NEW + "\t" + ref if any(c[0] == "push" for c in calls) else ""
            if args == ("diff", "--name-only", "--"):
                return "app/src/file.py"
            if args == ("diff", "--cached", "--name-only"):
                return "app/src/file.py"
            return ""
        def gh(_, *args):
            if args[:2] == ("repo", "view"):
                return '{"isPrivate":false}'
            if args[:2] == ("pr", "create"):
                return "https://github.com/example/draft/11"
            if args[:2] == ("pr", "view"):
                return json.dumps({"isDraft": True, "headRefOid": NEW,
                                   "baseRefName": "main", "url": "https://github.com/example/draft/11"})
            raise AssertionError(args)
        with patch.object(publication, "git", side_effect=git):
            with patch.object(publication, "gh", side_effect=gh):
                result = self.publish()
        self.assertEqual("VERIFIZIERT", result["status"])
        self.assertTrue(result["github_write_verified"])
        self.assertFalse(result["auto_merge"])
        self.assertFalse(result["ci_verified"])
        self.assertFalse(result["current_updated"])
        self.assertTrue((self.receipt_path.parent / ("DRAFT_" + RID + ".json")).is_file())


if __name__ == "__main__":
    unittest.main()
