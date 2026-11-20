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
