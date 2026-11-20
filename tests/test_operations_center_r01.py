"""Regression tests for additive read-only 666DEV Operations Center."""
import unittest
from devhub.intelligence.operations import FACETS, build_operations_center, facet_projection

def native(**changes):
    value = {
        "authority": "666DEV", "project_id": "demo-monorepo",
        "status": "VERIFIZIERT", "hub_commit": "a" * 40,
        "source_commit": "b" * 40, "profile_sha256": "c" * 64,
        "working_tree_clean": True,
        "working": {"checkpoint_id": "working"},
        "current": None, "return_anchor": "inspect", "acceptance": {},
    }
    value.update(changes)
    return value

class OperationsCenterTests(unittest.TestCase):
    def test_unbound_never_claims_project(self):
        result = build_operations_center(registry={"demo-monorepo":"x", "demo-linked":"y"})
        self.assertEqual("OFFEN", result["status"])
        self.assertEqual(["demo-linked", "demo-monorepo"], result["projects"])
        self.assertFalse(result["visual_daemon"]["primary_action"]["eligible"])
        self.assertFalse(result["visual_daemon"]["can_autowrite"])

    def test_facets_are_projections_only(self):
        result = build_operations_center(native())
        self.assertEqual(len(FACETS), len(result["facets"]))
        self.assertTrue(all(not item["writable"] for item in result["facets"]))
        self.assertEqual("NATIVE_SNAPSHOT_PROJECTION_ONLY", result["facets"][0]["rehydration"])
        self.assertIsNone(result["facets"][0]["last_verified_step"])
        with self.assertRaises(ValueError):
            facet_projection("lyvra", native())

    def test_conflict_held(self):
        value = build_operations_center(native(status="CONFLICT_QUARANTINE"))
        self.assertEqual("HOLD", value["visual_daemon"]["state"])
        self.assertEqual("READBACK_PENDING", value["facets"][0]["rehydration"])

    def test_dirty_recommends_impact(self):
        self.assertEqual("IMPACT", build_operations_center(
            native(status="PARTIAL", working_tree_clean=False))["visual_daemon"]["primary_action"]["action"][-1])

    def test_failed_tests_recommend_status(self):
        self.assertEqual("STATUS", build_operations_center(
            native(acceptance={"test": {"failed": 1}}))["visual_daemon"]["primary_action"]["action"][-1])

    def test_foreign_authority_disallowed(self):
        self.assertIsNone(build_operations_center(native(authority="LYVRA"))["project_id"])

    def test_unknown_status_fails_closed(self):
        result = build_operations_center(native(status="FAKE_PASS"))
        self.assertEqual("READBACK_PENDING", result["status"])
        self.assertEqual("HOLD", result["visual_daemon"]["state"])

    def test_r02_verified_checkpoint_projection(self):
        recorded = {"status": "VERIFIZIERT", "digest": "d"*64,
                    "reason": "Matches revision",
                    "checkpoint": {"state": "PAUSED", "last_verified_step": "audit",
                                   "obligations": ["host-test"], "evidence_ids": ["test-1"],
                                   "return_anchor": "next-step"}}
        projected = build_operations_center(native(), facet_records={"codeforge": recorded})
        codeforge = next(item for item in projected["facets"] if item["facet_id"] == "codeforge")
        self.assertEqual("VERIFIZIERT", codeforge["rehydration"])
        self.assertEqual("PAUSED", codeforge["work_state"])
        self.assertEqual(["host-test"], codeforge["obligations"])
        other = next(item for item in projected["facets"] if item["facet_id"] == "desktop")
        self.assertIsNone(other["work_state"])
        self.assertFalse(codeforge["writable"])

    def test_r02_stale_checkpoint_not_promoted(self):
        projected = build_operations_center(native(), facet_records={"codeforge": {
            "status": "PARTIAL", "digest": "e"*64,
            "reason": "Old revision", "checkpoint": None}})
        codeforge = next(item for item in projected["facets"] if item["facet_id"] == "codeforge")
        self.assertEqual("PARTIAL", codeforge["rehydration"])
        self.assertIsNone(codeforge["last_verified_step"])

    def test_no_host_claim(self):
        result = build_operations_center(native())
        self.assertEqual("OFFEN", result["host_acceptance"])
        self.assertEqual("OFFEN", result["plugin_acceptance"])
        self.assertFalse(result["visual_daemon"]["can_run_background"])

if __name__ == "__main__":
    unittest.main()
