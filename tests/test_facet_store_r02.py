"""R02 persistent sub-LiveCircle tests; no native Current or project writes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub import core
from devhub.intelligence import facet_store

PROOF = {"authority": "666DEV", "project_id": "demo-monorepo",
         "status": "VERIFIZIERT", "hub_commit": "a" * 40,
         "source_commit": "b" * 40, "profile_sha256": "c" * 64,
         "working_tree_clean": True, "working": None, "current": None}

class FacetStoreTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(tempfile.TemporaryDirectory())
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(core, "WORK", Path(self.temp)))
        self.enterContext(patch.object(core, "project_entries", return_value={"demo-monorepo": "projects/demo-monorepo/project.json"}))
        self.enterContext(patch("devhub.livecircle.snapshot", return_value=dict(PROOF)))

    def write(self, **changes):
        args = dict(project_id="demo-monorepo", facet_id="codeforge", native=dict(PROOF),
                    state="ACTIVE", last_verified_step="tested", obligations=["build"],
                    evidence_ids=["local:test:42"], return_anchor="continue")
        args.update(changes)
        return facet_store.save_checkpoint(**args)

    def test_read_absent_no_side_effects(self):
        self.assertEqual("OFFEN", facet_store.read_checkpoint("demo-monorepo", "codeforge", PROOF)["status"])
        self.assertFalse((Path(self.temp) / "facets").exists())

    def test_write_readback_and_cas(self):
        first = self.write()
        self.assertEqual("VERIFIZIERT", first["status"])
        self.assertEqual("tested", first["checkpoint"]["last_verified_step"])
        second = self.write(expected_digest=first["digest"], state="PAUSED")
        self.assertNotEqual(first["digest"], second["digest"])
        self.assertEqual("PAUSED", second["checkpoint"]["state"])
        with self.assertRaisesRegex(core.DevhubError, "CAS mismatch"):
            self.write(expected_digest=first["digest"])
        self.assertEqual("VERIFIZIERT", facet_store.read_checkpoint("demo-monorepo","codeforge",PROOF)["status"])

    def test_revision_change_never_promotes(self):
        self.write()
        changed = {**PROOF, "source_commit": "d" * 40}
        self.assertEqual("PARTIAL", facet_store.read_checkpoint("demo-monorepo", "codeforge", changed)["status"])
        with self.assertRaises(core.DevhubError):
            self.write(native=changed)

    def test_corrupt_record_quarantined(self):
        self.write()
        path = Path(self.temp) / "facets" / "demo-monorepo" / "codeforge.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["state"] = "COMPLETED"
        path.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual("CONFLICT_QUARANTINE", facet_store.read_checkpoint("demo-monorepo","codeforge",PROOF)["status"])
        with self.assertRaises(core.DevhubError):
            self.write()

    def test_invalid_authority_and_facet(self):
        with self.assertRaises(core.DevhubError):
            self.write(native={**PROOF, "authority": "LYVRA"})
        with self.assertRaises(core.DevhubError):
            self.write(facet_id="unknown")
        with self.assertRaises(core.DevhubError):
            self.write(project_id="../outside")

    def test_blocks_unsafe_write(self):
        for status in ("CONFLICT_QUARANTINE", "READBACK_PENDING", "WRITE_BLOCKED"):
            with self.subTest(status=status), self.assertRaises(core.DevhubError):
                self.write(native={**PROOF, "status": status})
        with self.assertRaises(core.DevhubError):
            self.write(native={**PROOF, "working_tree_clean": False})

    def test_same_key_lock_is_not_stolen(self):
        lock = Path(self.temp) / "facets" / "demo-monorepo" / "codeforge.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("owned by somebody else")
        with self.assertRaisesRegex(core.DevhubError, "locked"):
            self.write()
        self.assertTrue(lock.exists())

    def test_native_drift_before_write(self):
        with patch("devhub.livecircle.snapshot", return_value={**PROOF, "source_commit": "e"*40}):
            with self.assertRaisesRegex(core.DevhubError, "changed"):
                self.write()
        self.assertEqual("OFFEN", facet_store.read_checkpoint("demo-monorepo","codeforge", PROOF)["status"])

    def test_saved_source_pointer_drives_readback(self):
        self.write()
        changed = {**PROOF, "working": {"checkpoint_id": "different"}}
        self.assertEqual("PARTIAL", facet_store.read_checkpoint("demo-monorepo","codeforge", changed)["status"])

if __name__ == "__main__":
    unittest.main()
