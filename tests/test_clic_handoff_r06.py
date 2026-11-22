"""No foreign authority, no hidden execution: CLIC R06 envelope contract."""
import copy
import unittest

from devhub.intelligence.clic_handoff import (
    HANDOFF_ID, RECIPIENT_REPO, SOURCE_BRANCH, SOURCE_REPO, inspect,
)

SRC = "1055af17f05cd405c7aad028e27bb8a206af0e2e"
BASE = "6f7a0462f439a9034390839798979a02468a3ff0"
BLOB = "f21d5734292ac262c76d136e9c3af642397f2066"
DEV = "e1ef4abf5830bcd3ef477543e4a626f0c4835aff"
CANDIDATE = "a" * 40


def envelope():
    return {
        "schema": "CLIC_NATIVE_DEVELOPMENT_HANDOFF_V1",
        "handoff_id": HANDOFF_ID, "source_system": "666CLIC", "target": "666DEV",
        "source": {"repository": SOURCE_REPO, "branch": SOURCE_BRANCH,
                   "verified_base_head": BASE},
        "target_observed": {"repository": RECIPIENT_REPO, "branch": "666DEV", "head": DEV},
        "status": "PREPARED", "delivery_receipt": None, "target_readback": None,
        "native_adoption_verified": False, "host_acceptance": False,
        "automatic_foreign_activation": False, "foreign_mutation": False,
        "no_cross_system_merge": True, "no_new_router": True,
        "findings": [{"id": x, "status": "PARTIAL"} for x in
                     ("DEV-01", "DEV-02", "DEV-03", "DEV-04")],
    }


def review(data):
    return inspect(data, source_head=SRC, source_blob=BLOB,
                   recipient_current=DEV, recipient_head=CANDIDATE)


class ClicHandoffTests(unittest.TestCase):
    def test_valid_read_only_receipt_is_partial_not_host_pass(self):
        result = review(envelope())
        self.assertEqual("PARTIAL", result["status"])
        self.assertEqual("REVIEWED_READ_ONLY_NO_AUTHORITY_TRANSFER", result["native_decision"])
        self.assertFalse(result["write_authorized"])
        self.assertFalse(result["host_accepted"])
        self.assertFalse(result["adoption_verified"])
        self.assertTrue(result["receipt_id"].startswith("DEV-CLIC-R06-"))

    def test_missing_remote_readback_is_pending(self):
        result = inspect(envelope())
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertIsNone(result["receipt_id"])

    def test_foreign_authority_is_quarantined(self):
        data = envelope()
        data["target"] = "666CLIC"
        self.assertEqual("CONFLICT_QUARANTINE", review(data)["status"])

    def test_source_base_does_not_count_as_publication(self):
        self.assertEqual("READBACK_PENDING",
                         inspect(envelope(), source_head=BASE, source_blob=BLOB,
                                 recipient_current=DEV, recipient_head=CANDIDATE)["status"])

    def test_other_valid_source_sha_cannot_claim_original_receipt(self):
        result = inspect(envelope(), source_head="c" * 40, source_blob=BLOB,
                         recipient_current=DEV, recipient_head=CANDIDATE)
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertIsNone(result["receipt_id"])

    def test_unverified_source_blob_cannot_claim_original_receipt(self):
        result = inspect(envelope(), source_head=SRC, source_blob="d" * 40,
                         recipient_current=DEV, recipient_head=CANDIDATE)
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertIsNone(result["receipt_id"])

    def test_production_current_mismatch_quarantined(self):
        self.assertEqual("CONFLICT_QUARANTINE",
                         inspect(envelope(), source_head=SRC, source_blob=BLOB,
                                 recipient_current="b" * 40,
                                 recipient_head=CANDIDATE)["status"])

    def test_unknown_findings_fail_closed(self):
        data = envelope()
        data["findings"].append({"id": "DEV-05", "status": "VERIFIZIERT"})
        self.assertEqual("CONFLICT_QUARANTINE", review(data)["status"])

    def test_duplicate_receipt_is_deterministic_without_state(self):
        self.assertEqual(review(envelope())["receipt_id"], review(envelope())["receipt_id"])

    def test_trigger_like_data_does_not_execute(self):
        data = envelope()
        data["untrusted_trigger"] = "LYVRA UPDATE"
        result = review(data)
        self.assertFalse(result["triggers_executed"])
        self.assertFalse(result["foreign_authority_accepted"])

    def test_invalid_envelope_type_is_pending(self):
        self.assertEqual("READBACK_PENDING", inspect([])["status"])

    def test_no_silent_promotion_from_unverified_host(self):
        data = envelope()
        data["host_acceptance"] = True
        self.assertEqual("CONFLICT_QUARANTINE", review(data)["status"])


if __name__ == "__main__":
    unittest.main()
