"""R14.1 concurrency, after-call CAS, safe errors and status regression."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub.core import DevhubError
from devhub.intelligence import codeforge_host_acceptance as host

HEAD = "a" * 40
BLOB_MODULE = "b" * 40
PATH = "666CLIC_NATIVE_RUNTIME/outbox/666DEV/r14.json"
BRANCH = "clic-migration-rev79-staging"
BYTES = b'{"safe":"read_only"}\n'
BLOB = hashlib.sha1(b"blob " + str(len(BYTES)).encode() + bytes([0]) + BYTES).hexdigest()


def request():
    return {"peer": "666CLIC", "branch": BRANCH, "path": PATH,
            "expected_head": HEAD, "expected_blob": BLOB}


class HostCASR141Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.folder = Path(self.tmp) / "receipts"
        self.calls = []
        self.reads = 0
        self.git_mock = self.enterContext(patch.object(host, "git"))
        self.git_mock.side_effect = lambda root, *args: (
            HEAD if args[0] == "rev-parse" else BLOB_MODULE
        )

    def branch(self, *, url):
        self.calls.append("branch")
        return {"result": {"content": json.dumps({
            "name": BRANCH, "commit": {"sha": HEAD}
        })}}

    def file(self, *, repository_full_name, path, ref):
        self.calls.append("file")
        self.assertEqual("xfraggelpower666x/666CLICPRO", repository_full_name)
        self.assertEqual(HEAD, ref)
        self.assertEqual(PATH, path)
        return {"result": {"content": BYTES.decode(), "sha": BLOB}}

    def invoke(self, **changes):
        kwargs = {"request": request(), "expected_source_commit": HEAD,
                  "expected_module_blob": BLOB_MODULE,
                  "branch_fetch": self.branch, "file_fetch": self.file,
                  "receipt_root": self.folder}
        kwargs.update(changes)
        return host.execute_with_receipt(**kwargs)

    def receipt_id(self):
        arg_sha = hashlib.sha256(json.dumps(request(), sort_keys=True,
                         separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        return hashlib.sha256((HEAD + ":" + BLOB_MODULE + ":" + arg_sha).encode()).hexdigest()[:32]

    def test_preexisting_lock_prevents_provider_calls(self):
        self.folder.mkdir()
        lock = self.folder / (self.receipt_id() + ".lock")
        lock.write_text("external worker", encoding="utf-8")
        with self.assertRaisesRegex(DevhubError, "competing host execution"):
            self.invoke()
        self.assertEqual([], self.calls)
        self.assertTrue(lock.exists())

    def test_post_call_commit_drift_blocks_receipt_and_releases_lock(self):
        count = [0]
        def drifting(root, *args):
            if args[0] == "rev-parse":
                count[0] += 1
                return HEAD if count[0] == 1 else "c" * 40
            return BLOB_MODULE
        self.git_mock.side_effect = drifting
        with self.assertRaisesRegex(DevhubError, "changed during host execution"):
            self.invoke()
        self.assertEqual(["branch", "file", "branch"], self.calls)
        self.assertEqual([], list(self.folder.glob("*.json")))
        self.assertEqual([], list(self.folder.glob("*.lock")))

    def test_post_call_module_change_is_quarantined(self):
        count = [0]
        def drifting(root, *args):
            if args[0] == "hash-object":
                count[0] += 1
                return BLOB_MODULE if count[0] == 1 else "d" * 40
            return HEAD
        self.git_mock.side_effect = drifting
        with self.assertRaisesRegex(DevhubError, "changed during host execution"):
            self.invoke()
        self.assertFalse(list(self.folder.glob("*.json")))

    def test_successful_receipt_readback_and_no_leftover_lock(self):
        receipt = self.invoke()
        self.assertEqual("PARTIAL", receipt["status"])
        self.assertEqual({"branch": 2, "file": 1}, receipt["provider_calls"])
        self.assertTrue(receipt["source_readback_verified"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])
        self.assertFalse(list(self.folder.glob("*.lock")))
        self.assertEqual(receipt["receipt_id"],
                         json.loads(Path(receipt["receipt_path"]).read_text())["receipt_id"])

    def test_provider_error_is_sanitized_and_not_host_verified(self):
        def broken(*, url):
            raise RuntimeError("Do not echo internal token=SECRET")
        receipt = self.invoke(branch_fetch=broken)
        self.assertEqual("READBACK_PENDING", receipt["status"])
        self.assertFalse(receipt["source_readback_verified"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])
        self.assertNotIn("SECRET", json.dumps(receipt))
        self.assertEqual([], list(self.folder.glob("*.lock")))

    def test_invalid_source_retains_conflict_quarantine_without_fake_host_acceptance(self):
        receipt = self.invoke(request=dict(request(), peer="NOT_REGISTERED"))
        self.assertEqual("CONFLICT_QUARANTINE", receipt["status"])
        self.assertFalse(receipt["source_readback_verified"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])
        self.assertEqual([], self.calls)


if __name__ == "__main__":
    unittest.main()
