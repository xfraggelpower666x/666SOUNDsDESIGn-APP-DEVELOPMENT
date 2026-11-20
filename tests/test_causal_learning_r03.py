import unittest
from devhub.intelligence.causal_learning import plan_revalidation, review_outcome

PROJECT = 'demo-monorepo'
REV = 'b'*40
IMPACT = {'project_id': PROJECT, 'head': REV, 'base': 'a'*40,
          'changed_paths': ['src/demo_app/main.py'], 'fallback_reasons': [],
          'checks': [{'path': 'tests/a.py', 'disposition': 'RECHECK',
                      'chains': [['src/demo_app/main.py', 'tests/a.py']],
                      'reasons': ['changed input reaches this test']},
                     {'path': 'tests/b.py', 'disposition': 'UNIMPACTED',
                      'chains': [], 'reasons': ['not related']}]}
CANDIDATE = {'project_id': PROJECT, 'facet_id': 'codeforge',
             'source_revision': REV, 'hypothesis': 'Code path A triggers B',
             'counterexample': 'A changes, B remains stable'}

class CausalLearningR03Tests(unittest.TestCase):
    def test_recheck_preserves_chains_and_unimpacted(self):
        p = plan_revalidation(IMPACT, project_id=PROJECT, revision=REV)
        self.assertEqual('ABGELEITET', p['status'])
        self.assertEqual([True, False], [c['requires_revalidation'] for c in p['checks']])
        self.assertEqual('OFFEN', p['acceptance'])

    def test_unknown_revision_fails_closed(self):
        p = plan_revalidation(IMPACT, project_id=PROJECT, revision='d'*40)
        self.assertEqual('READBACK_PENDING', p['status'])
        self.assertTrue(p['recheck_all'])

    def test_fallback_forces_all_tests(self):
        p = plan_revalidation({**IMPACT, 'fallback_reasons': ['graph unresolved']},
                              project_id=PROJECT, revision=REV)
        self.assertEqual([True, True], [c['requires_revalidation'] for c in p['checks']])

    def test_unknown_disposition_rejected(self):
        p = plan_revalidation({**IMPACT, 'checks': [{**IMPACT['checks'][0], 'disposition':'PASS'}]},
                              project_id=PROJECT, revision=REV)
        self.assertEqual('CONFLICT_QUARANTINE', p['status'])

    def test_empty_check_inventory_with_changed_source_requires_recheck(self):
        report = plan_revalidation({**IMPACT, 'checks': []}, project_id=PROJECT, revision=REV)
        self.assertTrue(report['recheck_all'])
        self.assertIn('no declared test checks', report['fallback_reasons'][-1])

    def test_unscoped_or_wrong_facet_receipts_are_not_validated(self):
        for evidence in ({'project_id':PROJECT, 'source_revision':REV, 'outcome':'supports'},
                         {'project_id':PROJECT, 'source_revision':REV,
                          'facet_id':'repomind', 'outcome':'supports'}):
            with self.subTest(evidence=evidence):
                report = review_outcome(CANDIDATE, observed_receipts=[evidence])
                self.assertEqual('READBACK_PENDING', report['status'])
                self.assertEqual(0, report['matching_receipts'])

    def test_unknown_outcome_does_not_count(self):
        evidence = {'project_id':PROJECT, 'facet_id':'codeforge',
                    'source_revision':REV, 'outcome':'automatically-approved'}
        self.assertEqual('READBACK_PENDING',
                         review_outcome(CANDIDATE, observed_receipts=[evidence])['status'])

    def test_outcome_no_receipts_pending(self):
        r = review_outcome(CANDIDATE)
        self.assertEqual('READBACK_PENDING', r['status'])
        self.assertEqual('FORBIDDEN', r['promotion'])

    def test_outcome_receipt_is_not_independent_proof(self):
        r = review_outcome(CANDIDATE, observed_receipts=[{'project_id':PROJECT, 'facet_id':'codeforge',
            'source_revision':REV, 'outcome':'supports'}])
        self.assertEqual('VORGESCHLAGEN', r['status'])
        self.assertEqual('OFFEN', r['independent_verification'])
        self.assertFalse(r['writes'])

    def test_contradiction_retained(self):
        r = review_outcome(CANDIDATE, observed_receipts=[{'project_id':PROJECT, 'facet_id':'codeforge',
            'source_revision':REV, 'outcome':'contradicts'}])
        self.assertEqual('REVIEW_REQUIRED', r['contradiction_control'])
        self.assertEqual(1, r['contradictions'])

    def test_foreign_receipt_not_accepted(self):
        r = review_outcome(CANDIDATE, observed_receipts=[{'project_id':'foreign',
            'source_revision':REV,'outcome':'supports'}])
        self.assertEqual('READBACK_PENDING', r['status'])

if __name__ == '__main__':
    unittest.main()
