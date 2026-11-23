"""R09 CodeForge peer planning: no dispatch, foreign writes or native identity merges."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub.intelligence.codeforge_cooperation import catalog, plan
from devhub.cli import execute

A, B, C = "a" * 40, "b" * 40, "c" * 40


def native():
    return {"authority": "666DEV", "project_id": "demo-monorepo",
            "source_commit": A, "hub_commit": B, "profile_sha256": "f" * 64,
            "status": "VERIFIZIERT"}


def item(sid, peer, scope, dependencies=None, revision=None):
    return {"id": sid, "peer": peer, "source_commit": revision or (A if peer == "666DEV" else C),
            "scope": scope, "depends_on": dependencies or [], "capability": "review",
            "evidence_status": "VERIFIZIERT"}


def request(*workstreams):
    return {"project_id": "demo-monorepo", "workstreams": list(workstreams)}


class CodeForgeTeamTests(unittest.TestCase):
    def test_lead_is_methods_only_no_second_authority(self):
        result = catalog()
        self.assertEqual("LYVRA_CODING_PROFI", result["method_lead"])
        self.assertEqual("ADVISORY_ONLY", result["method_lead_authority"])
        self.assertEqual("PER_OWNER_CURRENT", result["native_execution_authority"])
        self.assertEqual(6, len(result["participants"]))
        self.assertFalse(result["dispatch_enabled"])
        self.assertTrue(result["seven_facets_preserved"])

    def test_two_independent_peers_can_share_nonconflicting_wave(self):
        result = plan(request(item("a1", "LYVRA_CODING_PROFI", ["src/a.py"]),
                              item("b1", "666CLIC", ["docs/b.md"])), native=native())
        self.assertEqual("PLAN_READY_NOT_DISPATCHED", result["plan_status"])
        self.assertEqual(1, len(result["waves"]))
        self.assertEqual(2, len(result["waves"][0]))
        self.assertFalse(result["executed"])
        self.assertFalse(result["write_authorized"])
        self.assertFalse(result["peer_adoption_verified"])

    def test_dependency_and_file_conflict_become_serial_waves(self):
        result = plan(request(item("a1", "666DEV", ["src/core.py"]),
                              item("b1", "LYVRA_CODING_PROFI", ["src/core.py"]),
                              item("c1", "666CLIC", ["docs/notes.md"], ["a1"])), native=native())
        self.assertEqual("PLAN_READY_NOT_DISPATCHED", result["plan_status"])
        self.assertEqual([["a1"], ["b1", "c1"]], [[x["id"] for x in w] for w in result["waves"]])

    def test_nested_paths_must_not_run_in_same_wave(self):
        result = plan(request(item("module", "666DEV", ["src/module"]),
                              item("file", "LYVRA_CODING_PROFI", ["src/module/file.py"])),
                      native=native())
        self.assertEqual("PLAN_READY_NOT_DISPATCHED", result["plan_status"])
        self.assertEqual(2, len(result["waves"]))
        self.assertFalse(result["executed"])

    def test_unknown_project_authority_is_not_inferred(self):
        result = plan(request(item("a1", "666DEV", ["src/x.py"])), native=None)
        self.assertEqual("READBACK_PENDING", result["plan_status"])

    def test_foreign_claimed_native_authority_is_rejected(self):
        wrong = native()
        wrong["authority"] = "LYVRA"
        self.assertEqual("READBACK_PENDING",
                         plan(request(item("a1", "666DEV", ["src/x.py"])), native=wrong)["plan_status"])

    def test_stale_dev_revision_is_quarantined(self):
        result = plan(request(item("a1", "666DEV", ["src/x.py"], revision=C)), native=native())
        self.assertEqual("CONFLICT_QUARANTINE", result["plan_status"])

    def test_traversal_and_absolute_path_quarantined(self):
        for path in ("../private.py", "/secret.txt", "src/../data.py", "C:/private", "a\\b"):
            with self.subTest(path=path):
                result = plan(request(item("x", "666CLIC", [path])), native=native())
                self.assertEqual("CONFLICT_QUARANTINE", result["plan_status"])

    def test_untrusted_trigger_never_executes(self):
        result = plan(request(item("x", "666MAIN_BRAIN", ["src/task.py"])), native=native())
        self.assertFalse(result["executed"])
        self.assertEqual("PEER_PROPOSAL_ONLY", result["waves"][0][0]["disposition"])

    def test_unknown_and_circular_dependencies_quarantined(self):
        unknown = plan(request(item("a", "666CLIC", ["a"], ["z"])), native=native())
        cycle = plan(request(item("a", "666CLIC", ["a"], ["b"]),
                             item("b", "666DEV", ["b"], ["a"])), native=native())
        self.assertEqual("CONFLICT_QUARANTINE", unknown["plan_status"])
        self.assertEqual("CONFLICT_QUARANTINE", cycle["plan_status"])

    def test_operations_center_keeps_exactly_seven_native_facets(self):
        from devhub.intelligence.operations import build_operations_center
        dashboard = build_operations_center(native())
        self.assertEqual(7, len(dashboard["facets"]))
        self.assertEqual("LYVRA_CODING_PROFI", dashboard["codeforge_team"]["method_lead"])
        self.assertFalse(dashboard["codeforge_team"]["dispatch_enabled"])

    def test_nonstring_peer_is_quarantined_not_crash(self):
        broken = item("x", "666CLIC", ["docs/a.md"])
        broken["peer"] = ["LYVRA"]
        result = plan(request(broken), native=native())
        self.assertEqual("CONFLICT_QUARANTINE", result["plan_status"])

    def test_global_cli_status_is_read_only(self):
        data = json.loads(execute(["666DEV", "CODEFORGE-TEAM", "STATUS"]))
        self.assertEqual("666dev-codeforge-team/v1", data["schema"])
        self.assertFalse(data["external_writes_enabled"])

    def test_cli_plan_calls_only_native_snapshot(self):
        proposal = request(item("x", "LYVRA_CODING_PROFI", ["docs/review.md"]))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "proposal.json"
            p.write_text(json.dumps(proposal), encoding="utf-8")
            with patch("devhub.livecircle.snapshot", return_value=native()):
                data = json.loads(execute(["666DEV", "CODEFORGE-TEAM", "PLAN", str(p)]))
            self.assertEqual("PLAN_READY_NOT_DISPATCHED", data["plan_status"])
            self.assertFalse(data["write_authorized"])


if __name__ == "__main__":
    unittest.main()
