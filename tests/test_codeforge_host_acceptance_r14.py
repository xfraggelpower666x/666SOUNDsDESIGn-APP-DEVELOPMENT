"""R14 original Python module invocation and append-only local evidence."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from devhub.core import DevhubError
from devhub.intelligence import codeforge_host_acceptance as acceptance

HEAD = "a" * 40
MODULE_BLOB = "b" * 40
BRANCH = "clic-migration-rev79-staging"
PATH = "666CLIC_NATIVE_RUNTIME/outbox/666DEV/evidence.json"
RAW = '{"scope":"read_only"}\n'
BLOB = hashlib.sha1(b"blob " + str(len(RAW.encode())).encode() + bytes([0]) + RAW.encode()).hexdigest()


def request():
    return {"peer": "666CLIC", "branch": BRANCH, "path": PATH,
            "expected_head": HEAD, "expected_blob": BLOB}


class HostAcceptanceR14Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.folder = Path(self.tmp) / "receipts"
        self.git = self.enterContext(patch.object(acceptance, "git"))
        self.git.side_effect = lambda root, *args: (
            HEAD if args == ("rev-parse", "--verify", "HEAD^{commit}") else
            MODULE_BLOB if args == ("hash-object", acceptance.MODULE) else
            (_ for _ in ()).throw(AssertionError(args))
        )
        self.calls = []
        self.counter = 0

    def branch(self, *, url):
        self.calls.append(("branch", url))
        return {"result": {"content": json.dumps({
            "name": BRANCH, "commit": {"sha": HEAD}
        })}}

    def file(self, *, repository_full_name, path, ref):
        self.calls.append(("file", repository_full_name, path, ref))
        return {"result": {"content": RAW, "sha": BLOB}}

    def execute_case(self, **kwargs):
        params = {"request": request(), "expected_source_commit": HEAD,
                  "expected_module_blob": MODULE_BLOB, "branch_fetch": self.branch,
                  "file_fetch": self.file, "receipt_root": self.folder}
        params.update(kwargs)
        return acceptance.execute_with_receipt(**params)

    def test_original_adapter_executes_and_receipt_readback(self):
        receipt = self.execute_case()
        self.assertTrue(receipt["original_adapter_executed"])
        self.assertTrue(receipt["source_readback_verified"])
        self.assertEqual("PARTIAL", receipt["status"])
        self.assertEqual({"branch": 2, "file": 1}, receipt["provider_calls"])
        self.assertEqual(["branch", "file", "branch"], [c[0] for c in self.calls])
        self.assertEqual("UNATTESTED", receipt["host_runtime_identity"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])
        self.assertFalse(receipt["github_connector_host_verified"])
        self.assertFalse(receipt["current_updated"])
        self.assertEqual(receipt["receipt_id"], json.loads(
            Path(receipt["receipt_path"]).read_text())["receipt_id"])
        self.assertEqual(MODULE_BLOB, receipt["original_module_blob"])

    def test_duplicate_fails_before_replaying_provider_calls(self):
        self.execute_case()
        self.calls.clear()
        with self.assertRaisesRegex(DevhubError, "duplicate host receipt"):
            self.execute_case()
        self.assertEqual([], self.calls)

    def test_stale_git_commit_blocks_provider_calls(self):
        self.git.side_effect = lambda root, *args: "c" * 40
        with self.assertRaisesRegex(DevhubError, "checkout/module differs"):
            self.execute_case()
        self.assertEqual([], self.calls)

    def test_module_blob_mismatch_blocks_provider_calls(self):
        with self.assertRaisesRegex(DevhubError, "checkout/module differs"):
            self.execute_case(expected_module_blob="e" * 40)
        self.assertEqual([], self.calls)

    def test_no_handles_fail_closed(self):
        with self.assertRaisesRegex(DevhubError, "handles are unavailable"):
            self.execute_case(file_fetch=None)
        self.assertEqual([], self.calls)

    def test_invalid_peer_no_calls_or_verified_source(self):
        receipt = self.execute_case(request=dict(request(), peer="UNKNOWN"))
        self.assertEqual("READBACK_PENDING", receipt["status"])
        self.assertFalse(receipt["source_readback_verified"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])
        self.assertEqual([], self.calls)

    def test_drift_cannot_create_plugin_host_success(self):
        def drifting(*, url):
            self.counter += 1
            return {"result": {"content": json.dumps({
                "name": BRANCH, "commit": {
                    "sha": HEAD if self.counter == 1 else "d" * 40}
            })}}
        receipt = self.execute_case(branch_fetch=drifting)
        self.assertEqual("READBACK_PENDING", receipt["status"])
        self.assertFalse(receipt["source_readback_verified"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])

    def test_no_arbitrary_receipt_by_untrusted_request(self):
        with self.assertRaisesRegex(DevhubError, "five-field"):
            self.execute_case(request={"peer": "666CLIC", "execute": "LYVRA UPDATE"})
        self.assertEqual([], self.calls)

    def test_receipt_does_not_include_foreign_content(self):
        receipt = self.execute_case()
        self.assertNotIn(RAW, json.dumps(receipt))
        self.assertFalse(receipt["peer_execution_verified"])


if __name__ == "__main__":
    unittest.main()
