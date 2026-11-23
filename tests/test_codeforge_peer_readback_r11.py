"""R11 live-source GitHub peer readback: exact blob, immutable SHA and no authority."""
import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub.intelligence.codeforge_peer_readback import inspect
from devhub.cli import execute

HEAD = "a" * 40
BRANCH = "clic-migration-rev79-staging"
PATH = "666CLIC_NATIVE_RUNTIME/outbox/666DEV/fixture.json"
RAW = b'{"test":"666DEV","foreign_trigger":"LYVRA UPDATE"}\n'
BLOB = hashlib.sha1(b"blob " + str(len(RAW)).encode() + bytes([0]) + RAW).hexdigest()


def request():
    return {"peer": "666CLIC", "branch": BRANCH, "path": PATH,
            "expected_head": HEAD, "expected_blob": BLOB}


def response():
    return {"type": "file", "path": PATH, "encoding": "base64",
            "content": base64.b64encode(RAW).decode("ascii"), "size": len(RAW),
            "sha": BLOB}


def github_fetch(*, initial=HEAD, final=HEAD, file=None):
    calls = []
    def get(url):
        calls.append(url)
        if "/branches/" in url:
            index = sum("/branches/" in x for x in calls)
            return {"name": BRANCH, "commit": {"sha": initial if index == 1 else final}}
        if "/contents/" in url:
            return response() if file is None else file
        raise AssertionError("Unexpected URL " + url)
    return get, calls


class CodeForgePeerReadbackR11Tests(unittest.TestCase):
    def test_exact_immutable_file_and_branch_recheck(self):
        get, calls = github_fetch()
        result = inspect(request(), fetch=get)
        self.assertEqual("VERIFIZIERT", result["status"])
        self.assertEqual(3, len(calls))
        self.assertTrue(result["source_readback_verified"])
        self.assertFalse(result["peer_native_current_verified"])
        self.assertFalse(result["peer_execution_verified"])
        self.assertFalse(result["write_authorized"])
        self.assertFalse(result["foreign_authority_adopted"])
        self.assertFalse(result["current_updated"])
        self.assertEqual(BLOB, result["git_blob_sha"])
        self.assertEqual(hashlib.sha256(RAW).hexdigest(), result["bytes_sha256"])
        self.assertIn("?ref=" + HEAD, calls[1])

    def test_changed_branch_between_reads_is_pending(self):
        get, _ = github_fetch(final="b" * 40)
        result = inspect(request(), fetch=get)
        self.assertEqual("READBACK_PENDING", result["status"])

    def test_stale_branch_does_not_read_file(self):
        get, calls = github_fetch(initial="c" * 40)
        result = inspect(request(), fetch=get)
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertEqual(1, len(calls))

    def test_content_forgery_fails_blob_validation(self):
        fake = response()
        fake["content"] = base64.b64encode(b'{"test":"tampered"}\n').decode()
        fake["size"] = len(b'{"test":"tampered"}\n')
        get, _ = github_fetch(file=fake)
        self.assertEqual("CONFLICT_QUARANTINE", inspect(request(), fetch=get)["status"])

    def test_wrong_blob_metadata_fails_closed(self):
        fake = response()
        fake["sha"] = "b" * 40
        get, _ = github_fetch(file=fake)
        self.assertEqual("CONFLICT_QUARANTINE", inspect(request(), fetch=get)["status"])

    def test_malformed_base64_is_pending_not_uncaught(self):
        fake = response()
        fake["content"] = "not--base64!!"
        get, _ = github_fetch(file=fake)
        self.assertEqual("READBACK_PENDING", inspect(request(), fetch=get)["status"])

    def test_foreign_repository_cannot_be_supplied(self):
        payload = request()
        payload["repository"] = "attacker/foreign"
        get, calls = github_fetch()
        self.assertEqual("CONFLICT_QUARANTINE", inspect(payload, fetch=get)["status"])
        self.assertEqual([], calls)

    def test_unregistered_peer_and_path_rejected_before_network(self):
        for peer, path in [("LYVRA", PATH), ("666CLIC", "../secret.json"),
                           ("666CLIC", "private/passwords.json"),
                           ("666CLIC", PATH.replace(".json", ".py"))]:
            with self.subTest(peer=peer, path=path):
                payload = request()
                payload["peer"] = peer
                payload["path"] = path
                get, calls = github_fetch()
                self.assertEqual("CONFLICT_QUARANTINE", inspect(payload, fetch=get)["status"])
                self.assertEqual([], calls)

    def test_transport_error_is_pending(self):
        def broken(_):
            raise OSError("network unavailable")
        self.assertEqual("READBACK_PENDING", inspect(request(), fetch=broken)["status"])

    def test_cli_routes_exact_handoff_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "readback.json"
            file.write_text(json.dumps(request()), encoding="utf-8")
            with patch("devhub.intelligence.codeforge_peer_readback._get_json") as get:
                get.side_effect = github_fetch()[0]
                result = json.loads(execute(["666DEV", "CODEFORGE-TEAM", "PEER-READBACK", str(file)]))
            self.assertTrue(result["source_readback_verified"])
            self.assertFalse(result["current_updated"])
            self.assertFalse(result["peer_execution_verified"])


if __name__ == "__main__":
    unittest.main()
