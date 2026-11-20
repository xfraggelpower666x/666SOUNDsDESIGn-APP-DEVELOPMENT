"""666DEV R03: evidence-bound causal test planning and outcome proposals.

Pure data transformations: no repo I/O, network access, learned-state mutation,
commands or auto-promotion. Consumes project_impact() output and native receipts.
"""
from __future__ import annotations

from collections.abc import Mapping

SCHEMA = '666dev-r03-causal-review/v1'
ALLOWED = {'RECHECK', 'UNIMPACTED'}
STATES = {'VORGESCHLAGEN', 'READBACK_PENDING', 'CONFLICT_QUARANTINE'}


def plan_revalidation(impact: Mapping, *, project_id: str, revision: str) -> dict:
    """Convert native impact results into an explainable recheck plan.

    The planner never invalidates persisted receipts; it marks evidence as
    requiring revalidation at a new revision. UNKNOWN => full safe recheck.
    """
    valid = isinstance(impact, Mapping) and impact.get('project_id') == project_id
    valid &= isinstance(impact.get('checks'), list)
    valid &= isinstance(impact.get('head'), str) and impact.get('head') == revision
    if not valid:
        return {'schema': SCHEMA, 'status': 'READBACK_PENDING', 'project_id': project_id,
                'source_revision': revision, 'checks': [], 'recheck_all': True,
                'reason': 'Missing or mismatched native impact evidence.'}
    plans = []
    for check in impact['checks']:
        if not isinstance(check, Mapping) or not isinstance(check.get('path'), str):
            return {'schema': SCHEMA, 'status': 'CONFLICT_QUARANTINE',
                    'project_id': project_id, 'source_revision': revision, 'checks': [],
                    'recheck_all': True, 'reason': 'Malformed test dependency record.'}
        flag = check.get('disposition')
        if flag not in ALLOWED or not isinstance(check.get('chains'), list) or not isinstance(check.get('reasons'), list):
            return {'schema': SCHEMA, 'status': 'CONFLICT_QUARANTINE',
                    'project_id': project_id, 'source_revision': revision, 'checks': [],
                    'recheck_all': True, 'reason': 'Unrecognized impact disposition.'}
        plans.append({'path': check['path'], 'disposition': flag,
                      'requires_revalidation': flag == 'RECHECK',
                      'causal_chains': check['chains'], 'reasons': check['reasons'],
                      'acceptance': 'OFFEN'})
    fallback = impact.get('fallback_reasons')
    if not isinstance(fallback, list):
        fallback = ['Native impact fallback metadata missing.']
    if fallback:
        for item in plans:
            item['requires_revalidation'] = True
            item['disposition'] = 'RECHECK'
            item['reasons'] = list(dict.fromkeys([*item['reasons'], *fallback]))
    return {'schema': SCHEMA, 'status': 'ABGELEITET', 'project_id': project_id,
            'source_revision': revision, 'base_revision': impact.get('base'),
            'recheck_all': bool(fallback), 'changed_paths': impact.get('changed_paths', []),
            'checks': plans, 'fallback_reasons': fallback,
            'acceptance': 'OFFEN', 'applies_changes': False}


def review_outcome(candidate: Mapping, *, observed_receipts: list[dict] | None = None) -> dict:
    """Classify an outcome hypothesis, without learning or promoting a rule.

    A receipt supplied by the caller is not independently authenticated.
    An independent verifier is required in a subsequent integration gate.
    """
    if not isinstance(candidate, Mapping):
        return {'status': 'CONFLICT_QUARANTINE', 'reason': 'Candidate is not an object.'}
    fields = ('project_id', 'facet_id', 'source_revision', 'hypothesis', 'counterexample')
    if any(not isinstance(candidate.get(key), str) or not candidate[key].strip() for key in fields):
        return {'status': 'READBACK_PENDING', 'reason': 'Missing scoped candidate identity or falsifiable hypothesis.'}
    receipts = observed_receipts or []
    if not isinstance(receipts, list) or any(not isinstance(r, Mapping) for r in receipts):
        return {'status': 'CONFLICT_QUARANTINE', 'reason': 'Invalid receipt collection.'}
    matching = [r for r in receipts if r.get('project_id') == candidate['project_id']
                and r.get('source_revision') == candidate['source_revision']]
    contradictions = [r for r in matching if r.get('outcome') == 'contradicts']
    state = 'VORGESCHLAGEN' if matching else 'READBACK_PENDING'
    return {'schema': SCHEMA, 'status': state, 'project_id': candidate['project_id'],
            'facet_id': candidate['facet_id'], 'source_revision': candidate['source_revision'],
            'hypothesis': candidate['hypothesis'], 'counterexample': candidate['counterexample'],
            'matching_receipts': len(matching), 'contradictions': len(contradictions),
            'contradiction_control': 'REVIEW_REQUIRED' if contradictions else 'NONE_OBSERVED',
            'independent_verification': 'OFFEN', 'promotion': 'FORBIDDEN',
            'writes': False, 'learning_state_changed': False}
