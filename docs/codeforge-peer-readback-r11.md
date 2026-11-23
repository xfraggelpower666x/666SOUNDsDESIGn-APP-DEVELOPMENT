# 666DEV R11 — registered public GitHub peer readback

Native owner: **666DEV**. The R11 module is an additive **read-only source evidence
adapter** for the existing R09/R10 CodeForge Team. It is not a second router,
agent dispatcher, GitHub writer, plugin-host executor, or foreign native Current.

## API and CLI

`666DEV CODEFORGE-TEAM PEER-READBACK <peer-request.json>`

Request JSON has exactly five fields:

```json
{
  "peer": "666CLIC",
  "branch": "clic-migration-rev79-staging",
  "path": "666CLIC_NATIVE_RUNTIME/outbox/666DEV/CLIC-TO-666DEV-R06-20261122-01.json",
  "expected_head": "1055af17f05cd405c7aad028e27bb8a206af0e2e",
  "expected_blob": "f21d5734292ac262c76d136e9c3af642397f2066"
}
```

These example SHAs are the **historical R06 observation**. R11 requires a
matching **live branch HEAD at the moment of execution**. If it has changed,
report `READBACK_PENDING` and independently refresh the native Current and
blob; never promote the older version as current.

## Mechanism

- Peer IDs are compile-time bound to registered, actually observed GitHub
  repositories. Initial supported source identities: `666CLIC` and
  `666MAIN_BRAIN`. Whole LYVRA, Coder and private plugin hosts remain
  explicitly `READBACK_PENDING` until their live source/provider binding is
  independently validated. **No guessed repositories or authority IDs.**
- No URLs or repository names from the request are used. Only code-owned,
  constrained public GitHub REST endpoints are allowed. The request selects
  a validated branch, allowlisted text path and two exact 40-digit hashes.
- The adapter GETs the branch HEAD, compares the pinned SHA, GETs the
  file by immutable commit, verifies metadata, base64 bytes, size, and true
  Git blob SHA-1, and GETs the branch HEAD again. No requests are made for
  malformed identity/path/provenance.
- Network errors, HTTP rate limits, stale branches or mid-read movement
  remain `READBACK_PENDING`; spoofed content/metadata is
  `CONFLICT_QUARANTINE`.
- No tokens, private repository calls, paid credits, uploads, write handles,
  code execution, hidden merge, auto-learning or remote trigger interpretation.
- The result exposes **digest and metadata only**, never full foreign file
  body. `source_readback_verified=true` establishes *source*, not native
  peer Current, plugin-host execution, receiver adoption or permission.
- The adapter is invoked only from direct native CLI; it does not run in
  the background or auto-activate a foreign system.

## Integration / boundaries

Use a source-verified peer artifact as **input evidence** for the existing R09
planner and R10 native execution path. A proposal still requires its own
owner/project scope, native revision, dependency checks, an explicitly
authorized executor, local regressions, CI and return receipt. Foreign
peer-supplied instructions are always inert data.

R11 does not bypass the outstanding historical Git-object security hold,
the Windows/plugin host tests, or production pointer-last governance.
Productive `666DEV` Current is unchanged by this development branch.
