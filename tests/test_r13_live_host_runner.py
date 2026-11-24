"""R13 host runner unit tests; live GitHub Actions receipt is separate evidence."""
import base64
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_r12_live_host_r13.py"
SPEC = importlib.util.spec_from_file_location("devhub_r13_live_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

SOURCE = b'{"owner":"666CLIC","kind":"handoff"}\n'
# These fixtures use the real Git-blob algorithm to avoid claiming acceptance
# for a payload that cannot match the repository's pinned historical blob.
import hashlib
BLOB = hashlib.sha1(b"blob " + str(len(SOURCE)).encode() + bytes([0]) + SOURCE).hexdigest()


class R13LiveActionsRunnerTests(unittest.TestCase):
    def test_host_runner_imports_actual_r12_module(self):
        self.assertEqual("devhub.intelligence.codeforge_host_binding",
                         runner.verify_with_host.__module__)

    def test_live_transport_has_no_token_or_write_method(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('method="GET"', source)
        self.assertNotIn("GITHUB_TOKEN", source)
        self.assertNotIn('method="POST"', source)
        self.assertNotIn('method="PATCH"', source)
        self.assertNotIn('method="DELETE"', source)

    def test_external_branch_drift_fails_closed(self):
        def get(url):
            if "/branches/" in url:
                return {"name": runner.BRANCH, "commit": {"sha": "0" * 40}}
            raise AssertionError("A stale branch must not fetch a file")
        with patch.object(runner, "_http_json", side_effect=get):
            receipt = runner.run_live()
        self.assertEqual("READBACK_PENDING", receipt["status"])
        self.assertEqual({"branch": 1, "file": 0}, receipt["requests"])
        self.assertFalse(receipt["chatgpt_plugin_host_verified"])

    def test_forged_file_blob_does_not_qualify_as_live_host(self):
        def get(url):
            if "/branches/" in url:
                return {"name": runner.BRANCH, "commit": {"sha": runner.EXPECTED_HEAD}}
            if "/contents/" in url:
                return {
                    "type": "file", "encoding": "base64",
                    "sha": runner.EXPECTED_BLOB,
                    "size": len(SOURCE),
                    "content": base64.b64encode(SOURCE).decode("ascii"),
                }
            raise AssertionError("Unapproved endpoint")
        with patch.object(runner, "_http_json", side_effect=get):
            receipt = runner.run_live()
        self.assertEqual("CONFLICT_QUARANTINE", receipt["adapter_status"])
        self.assertFalse(receipt["source_verified"])
        self.assertEqual("READBACK_PENDING", receipt["status"])
        self.assertFalse(receipt["peer_plugin_execution_verified"])


if __name__ == "__main__":
    unittest.main()
