"""R10 real isolated Git-worktree regression; no external repo writes."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub import core
from devhub.core import DevhubError
from devhub.intelligence import codeforge_execution as execution


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                            text=True, check=True)
    return result.stdout.strip()


class NativeExecutableCodeForgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.base = Path(self.tmp)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init")
        self.source = self.repo / "app"
        (self.source / "src").mkdir(parents=True)
        self.target = self.source / "src" / "file.py"
        self.target.write_text("print('before')\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-m", "Safe baseline")
        self.head = git(self.repo, "rev-parse", "HEAD")
        self.work = self.base / "work"
        self.project_dir = self.base / "project"
        self.folder = self.project_dir / "state" / "patch-candidates"
        self.folder.mkdir(parents=True)
        self.profile = {
            "id": "r10demo", "source_mode": "monorepo", "source_path": "app",
            "expected_ref": "HEAD", "writable_paths": ["src"],
            "build_commands": [["python", "-m", "py_compile", "src/file.py"]],
        }
        self.native = {"authority": "666DEV", "project_id": "r10demo",
                       "source_commit": self.head, "hub_commit": self.head,
                       "profile_sha256": "f" * 64, "status": "VERIFIZIERT"}
        self.proposal = {
            "project_id": "r10demo",
            "workstreams": [{"id": "fix", "peer": "666DEV", "source_commit": self.head,
                             "scope": ["src/file.py"], "depends_on": [],
                             "capability": "repair", "evidence_status": "VERIFIZIERT"}],
        }
        self.candidate = {
            "schema_version": 1, "project_id": "r10demo", "candidate_id": "r10-safe",
            "base_commit": self.head, "status": "VORGESCHLAGEN",
            "patches": [{"path": "src/file.py", "content": "print('after')\n"}],
        }
        self.state = {"profile": self.profile, "source": self.source,
                      "project_dir": self.project_dir,
                      "revision": {"commit": self.head}}
        self.enterContext(patch.object(core, "WORK", self.work))
        self.enterContext(patch.object(execution, "WORK", self.work))
        self.enterContext(patch.object(execution, "rehydrate", return_value=self.state))

    def write_candidate(self):
        file = self.folder / "candidate.json"
        file.write_text(json.dumps(self.candidate), encoding="utf-8")
        return hashlib.sha256(file.read_bytes()).hexdigest()

    def execute(self, sha=None, proposal=None, workstream="fix"):
        return execution.execute_native(
            proposal if proposal is not None else self.proposal,
            workstream_id=workstream,
            candidate_relative="candidate.json",
            expected_candidate_sha256=sha if sha is not None else self.write_candidate(),
            native=self.native,
        )

    def test_real_isolated_patch_compile_and_receipt_readback(self):
        receipt = self.execute()
        self.assertTrue(receipt["isolated_patch_applied"])
        self.assertTrue(receipt["readback_verified"])
        self.assertTrue(receipt["local_build_verified"])
        self.assertEqual("PARTIAL", receipt["status"])
        self.assertFalse(receipt["github_write_verified"])
        self.assertFalse(receipt["tests_verified"])
        self.assertFalse(receipt["current_updated"])
        self.assertEqual("print('before')\n", self.target.read_text())
        self.assertEqual(self.head, git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(receipt["changed_file_sha256"]["src/file.py"],
                         hashlib.sha256(b"print('after')\n").hexdigest())
        saved = json.loads(Path(receipt["receipt_path"]).read_text())
        self.assertEqual(receipt["receipt_id"], saved["receipt_id"])
        isolated = Path(receipt["worktree"])
        self.assertEqual("print('after')\n", (isolated / "app/src/file.py").read_text())
        git(self.repo, "worktree", "remove", "--force", str(isolated))

    def test_wrong_digest_is_blocked_without_worktree(self):
        self.write_candidate()
        with self.assertRaisesRegex(DevhubError, "digest mismatch"):
            self.execute(sha="0" * 64)
        self.assertFalse((self.work / "worktrees").exists())

    def test_foreign_peer_cannot_execute(self):
        self.proposal["workstreams"][0]["peer"] = "666CLIC"
        with self.assertRaisesRegex(DevhubError, "only a first-wave 666DEV"):
            self.execute()

    def test_changed_revision_cannot_execute(self):
        self.proposal["workstreams"][0]["source_commit"] = "a" * 40
        with self.assertRaises(DevhubError):
            self.execute()

    def test_candidate_outside_approved_scope_is_blocked(self):
        self.candidate["patches"][0]["path"] = "src/another.py"
        with self.assertRaisesRegex(DevhubError, "reviewed workstream scope"):
            self.execute()

    def test_unknown_test_cost_does_not_claim_regression(self):
        receipt = self.execute()
        self.assertFalse(receipt["tests_verified"])
        self.assertFalse(receipt["publication_authorized"])
        git(self.repo, "worktree", "remove", "--force", receipt["worktree"])


if __name__ == "__main__":
    unittest.main()
