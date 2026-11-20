# 666DEV Operations Center · R01

STATUS=REPO_IMPLEMENTED_HOST_PENDING

## Source authority
Source of truth: `src/devhub/core.py`, `src/devhub/livecircle.py`,
`registry/projects.json` and project profiles. The new
`src/devhub/intelligence/operations.py` is a pure projection with no I/O.
It is not an independent LiveCircle/learning engine. The branch and exact
commit must be read before a currentness claim.

## Host surfaces
- CLI and existing LiveCircle: retained unchanged.
- Windows Control: new tab Operations Center, existing local server,
  GET `/api/operations-center?project=<registered-id>`.
- Existing Visualformen and Chart engine: retained; navigation links to it.
- ChatGPT plugin: adapter is requested but release and host parity are pending
  until plugin packaging, direct provider readback and host acceptance.

## Data semantics
`666dev-operations-center/v1` has authority, source, project id, status,
navigation, six scoped view projections, and advisory Visual Daemon. The
subfacet schema `666dev-facet-livecircle/v1` explicitly leaves unverified
last_verified_step null and obligations/evidence lists empty.

The menu chooses among existing tabs. The Daemon may suggest STATUS, IMPACT
or LIVECIRCLE, exclusively via existing user-triggered action pathways.
No new POST endpoint or direct automatic update is introduced.

## Architecture provenance
CLIC contributes sub-stream reachability semantics, LYVRA contextual
capability discovery, PFS controlled patch/rollback boundaries, STREAM
independent checks, MAIN BRAIN bounded conductor decisions. These are
design influences, not imports, authority transfer or host execution evidence.

## Completion gates
- Actual repository test + verifier on integrated source.
- GitHub CI and independent readback of integration commit.
- Real Windows .cmd launch and click-path acceptance.
- Plugin source publication, provider readback and fresh host acceptance.
- Persistent native subfacet ledger, causal test invalidation, supervised
  learning and safe healing remain separate follow-on work, not R01 claims.

## R02 · Persistent facet checkpoint and scoped rehydration

Implementation: `src/devhub/intelligence/facet_store.py`.
The private, ignored carrier is `.work/facets/<project-id>/<facet-id>.json`.
It is NOT a new Current pointer and never writes a source project.
Only the six registered 666DEV facet IDs are accepted.

- `FACET-STATUS <facet-id>` reads the facet record without mutation.
- `FACET-SAVE <facet-id> <input.json>` is an explicit local write action.
- A new record requires `expected_digest: null`; replacing an existing
  record requires exactly the last observed SHA-256 digest (CAS).
- The saved source binding includes 666DEV Hub HEAD, project commit, profile
  fingerprint and the existing Working/Current pointer objects.
- Before a write, a fresh native snapshot must still match that binding;
  if not, the write fails. Directory scope, exclusive lock and atomic JSON
  replacement protect concurrent local writers.
- After saving, the same bytes are reopened and independently compared.
- The Windows Operations Center reads these records through its existing
  loopback GET API. It does not provide a new write route.
- Stale revision -> PARTIAL; corrupt/modified record -> CONFLICT_QUARANTINE;
  unavailable native proof -> READBACK_PENDING. None is promoted to Live.
- The record binding being VERIFIZIERT **does not verify the truth of
  self-reported work-step or evidence identifiers**; `step_evidence_status`
  stays OFFEN until an independent receipt verification is added.

Input format for a deliberate native CLI save:

```json
{
  "state": "PAUSED",
  "last_verified_step": null,
  "obligations": ["Windows Host test open"],
  "evidence_ids": [],
  "return_anchor": "resume Windows tests at source revision",
  "expected_digest": null
}
```

State is READY, ACTIVE, WAITING, PAUSED or COMPLETED. Save is not a
background process, and no user input or saved handoff may itself trigger
the CLI command. The native root/project Current pointers remain untouched.

R03 candidates: causal test invalidation, outcome validation and learning;
cross-host synchronization of facet checkpoints and real Windows host tests.
