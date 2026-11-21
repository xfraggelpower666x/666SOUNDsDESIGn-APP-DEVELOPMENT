import unittest
from devhub.intelligence.coding_profi import trigger
from devhub.intelligence.operations import FACETS, build_operations_center
from devhub.intelligence.facet_store import FACET_IDS

PROJECT = "demo-monorepo"
NATIVE = {"authority":"666DEV", "project_id":PROJECT,"hub_commit":"a"*40,
          "source_commit":"b"*40, "profile_sha256":"c"*64,
          "status":"OFFEN", "working":None, "current":None, "return_anchor":None}

class CodingProfiFacetTests(unittest.TestCase):
    def test_registered_in_existing_facet_layers(self):
        self.assertIn("coding-profi", FACET_IDS)
        self.assertIn("coding-profi", [x[0] for x in FACETS])
        self.assertFalse(build_operations_center(NATIVE)['facets'][-1]['writable'])
    def test_foreign_native_source_is_untrusted(self):
        report=trigger("SYSTEMSTART", {**NATIVE,"authority":"LYVRA"}, project_id=PROJECT)
        self.assertEqual("READBACK_PENDING",report['status'])
        self.assertFalse(report['can_autoactivate_lyvra'])
    def test_handoff_roundtrip_read_only(self):
        save=trigger("NEW-CHAT", NATIVE, project_id=PROJECT)['handoff']
        report=trigger("NEXT-CHAT",NATIVE, project_id=PROJECT, handoff=save)
        self.assertTrue(report['handoff_accepted'])
        self.assertFalse(report['writable'])
    def test_stale_handoff_quarantined(self):
        save=trigger("NEW-CHAT",NATIVE,project_id=PROJECT)['handoff']
        changed={**NATIVE,'source_commit':'d'*40}
        self.assertEqual('CONFLICT_QUARANTINE', trigger('NEXT-CHAT',changed,project_id=PROJECT,handoff=save)['status'])
    def test_foreign_handoff_quarantined(self):
        self.assertEqual('CONFLICT_QUARANTINE',trigger('NEXT-CHAT',NATIVE,project_id=PROJECT,handoff={'authority':'LYVRA'})['status'])
    def test_next_step_does_not_execute(self):
        report=trigger('WEITER', NATIVE,project_id=PROJECT)
        self.assertFalse(report['executes_next_action'])
        self.assertIn('CAUSAL',report['next_action'])
    def test_corrupt_facet_checkpoint_stays_quarantined(self):
        saved = {'status': 'CONFLICT_QUARANTINE', 'checkpoint': None}
        report = trigger('SYSTEMSTART', NATIVE, project_id=PROJECT, saved=saved)
        self.assertEqual('CONFLICT_QUARANTINE', report['status'])
        self.assertEqual('CONFLICT_QUARANTINE', report['facet_checkpoint_status'])

    def test_stale_facet_checkpoint_remains_partial(self):
        saved = {'status': 'PARTIAL', 'checkpoint': None}
        report = trigger('STATUS', NATIVE, project_id=PROJECT, saved=saved)
        self.assertEqual('PARTIAL', report['status'])
        self.assertEqual('PARTIAL', report['facet_checkpoint_status'])

    def test_conflicted_facet_refuses_handoff_adoption(self):
        saved = {'status': 'CONFLICT_QUARANTINE', 'checkpoint': None}
        handoff = trigger('NEW-CHAT', NATIVE, project_id=PROJECT)['handoff']
        report = trigger('NEXT-CHAT', NATIVE, project_id=PROJECT,
                         saved=saved, handoff=handoff)
        self.assertFalse(report['handoff_accepted'])
        self.assertEqual('CONFLICT_QUARANTINE', report['status'])

    def test_changed_native_pointers_same_revision_quarantined(self):
        handoff = trigger('NEW-CHAT', NATIVE, project_id=PROJECT)['handoff']
        for field, value in (
            ('working', {'checkpoint_id': 'new-working', 'commit': 'b'*40}),
            ('current', {'checkpoint_id': 'new-current', 'commit': 'b'*40}),
            ('return_anchor', 'different-line'),
        ):
            with self.subTest(field=field):
                changed = {**NATIVE, field: value}
                report = trigger('NEXT-CHAT', changed, project_id=PROJECT, handoff=handoff)
                self.assertEqual('CONFLICT_QUARANTINE', report['status'])
                self.assertFalse(report.get('handoff_accepted', False))

    def test_partial_facet_handoff_not_adopted(self):
        saved = {'status': 'PARTIAL', 'checkpoint': None}
        handoff = trigger('NEW-CHAT', NATIVE, project_id=PROJECT, saved=saved)['handoff']
        report = trigger('NEXT-CHAT', NATIVE, project_id=PROJECT,
                         saved=saved, handoff=handoff)
        self.assertEqual('PARTIAL', report['status'])
        self.assertFalse(report['handoff_accepted'])

    def test_legacy_handoff_requires_native_revalidation(self):
        handoff = trigger('NEW-CHAT', NATIVE, project_id=PROJECT)['handoff']
        handoff.pop('continuity_binding')
        self.assertEqual('READBACK_PENDING',
                         trigger('NEXT-CHAT', NATIVE, project_id=PROJECT,
                                 handoff=handoff)['status'])

    def test_saved_facet_evidence_changes_invalidate_handoff(self):
        saved = {'status': 'VERIFIZIERT', 'digest':'a'*64,
                 'checkpoint': {'return_anchor': 'line-a',
                                'last_verified_step': 'step-1',
                                'obligations': ['finish-tests'],
                                'evidence_ids': ['receipt-a']}}
        handoff = trigger('NEW-CHAT', NATIVE, project_id=PROJECT, saved=saved)['handoff']
        report = trigger('NEXT-CHAT', NATIVE, project_id=PROJECT, saved=saved, handoff=handoff)
        self.assertTrue(report['handoff_accepted'])
        self.assertTrue(report['task_resumed'])
        changed = {**saved, 'digest':'b'*64}
        report = trigger('NEXT-CHAT', NATIVE, project_id=PROJECT,
                         saved=changed, handoff=handoff)
        self.assertEqual('CONFLICT_QUARANTINE', report['status'])

    def test_invalid_trigger_rejected(self):
        with self.assertRaises(ValueError):trigger('UPDATE',NATIVE,project_id=PROJECT)
    def test_missing_native_source_pending(self):
        self.assertEqual('READBACK_PENDING',trigger('STATUS',None,project_id=PROJECT)['status'])

if __name__ == '__main__': unittest.main()
