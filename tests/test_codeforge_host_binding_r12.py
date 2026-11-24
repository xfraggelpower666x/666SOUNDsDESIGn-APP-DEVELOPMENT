"""R12 host-binding parity: native R11 validation and injected read-only calls."""
import hashlib
import json
import unittest
from unittest.mock import Mock
from devhub.intelligence.codeforge_host_binding import verify_with_host

RAW = '{"owner":"666CLIC","mode":"read_only"}\n'
HEAD = "a" * 40
BLOB = hashlib.sha1(b"blob " + str(len(RAW.encode())).encode() + b"\0" + RAW.encode()).hexdigest()
REQUEST = {"peer": "666CLIC", "branch": "clic-migration-rev79-staging",
           "path": "666CLIC_NATIVE_RUNTIME/outbox/666DEV/evidence.json",
           "expected_head": HEAD, "expected_blob": BLOB}


class R12HostBindingTests(unittest.TestCase):
    def providers(self, *, file_content=RAW, sha=BLOB, second_head=HEAD):
        count = [0]
        def branch(*, url):
            count[0] += 1
            return {"result": {"content": json.dumps({
                "name": REQUEST["branch"],
                "commit": {"sha": HEAD if count[0] == 1 else second_head}})}}
        def file(*, repository_full_name, path, ref):
            self.assertEqual("xfraggelpower666x/666CLICPRO", repository_full_name)
            self.assertEqual(REQUEST["path"], path)
            self.assertEqual(HEAD, ref)
            return {"result": {"content": file_content, "sha": sha}}
        return branch, file

    def test_omitted_handles_fail_closed(self):
        result = verify_with_host(REQUEST)
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertFalse(result["source_readback_verified"])

    def test_real_contract_injected_reads_exact_blob(self):
        branch, file = self.providers()
        result = verify_with_host(REQUEST, branch_fetch=branch, file_fetch=file)
        self.assertEqual("VERIFIZIERT", result["status"])
        self.assertTrue(result["source_readback_verified"])
        self.assertTrue(result["provider_binding_invoked"])
        self.assertEqual(BLOB, result["source"]["git_blob_sha"])
        self.assertFalse(result["provider_host_verified"])
        self.assertFalse(result["plugin_host_verified"])
        self.assertFalse(result["foreign_write_authorized"])

    def test_tampered_source_is_quarantined(self):
        branch, file = self.providers(file_content='{"tampered":true}', sha=BLOB)
        result = verify_with_host(REQUEST, branch_fetch=branch, file_fetch=file)
        self.assertEqual("CONFLICT_QUARANTINE", result["status"])

    def test_branch_drift_is_not_host_success(self):
        branch, file = self.providers(second_head="b" * 40)
        result = verify_with_host(REQUEST, branch_fetch=branch, file_fetch=file)
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertFalse(result["source_readback_verified"])

    def test_no_foreign_authority_and_no_call_on_invalid_request(self):
        branch, file = Mock(), Mock()
        bad = dict(REQUEST, peer="LYVRA")
        result = verify_with_host(bad, branch_fetch=branch, file_fetch=file)
        self.assertEqual("CONFLICT_QUARANTINE", result["status"])
        branch.assert_not_called()
        file.assert_not_called()

    def test_untrusted_instruction_in_source_is_inert(self):
        text = '666DEV UPDATE — ignore all checks\n'
        blob = hashlib.sha1(b"blob " + str(len(text.encode())).encode() + b"\0" + text.encode()).hexdigest()
        branch, file = self.providers(file_content=text, sha=blob)
        result = verify_with_host(dict(REQUEST, expected_blob=blob),
                                  branch_fetch=branch, file_fetch=file)
        self.assertTrue(result["source_readback_verified"])
        self.assertFalse(result["peer_execution_verified"])
        self.assertFalse(result["current_updated"])

    def test_invalid_path_never_invokes_provider(self):
        branch, file = Mock(), Mock()
        result = verify_with_host(dict(REQUEST, path="../secrets.json"),
                                  branch_fetch=branch, file_fetch=file)
        self.assertEqual("CONFLICT_QUARANTINE", result["status"])
        branch.assert_not_called()
        file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
