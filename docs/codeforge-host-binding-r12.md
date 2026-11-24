# 666DEV R12 — Host-bound Peer CodeForge Readback

**Native Authority:** 666DEV. **Parent basis:** R11 at `c3aa9dd28541c402c4a57d3224e339531e631141`.
This update extends the existing CodeForge R09 planner, R10 isolated native executor and R11 public GitHub source readback. No eighth facet, global router, foreign Current, installed plugin source import or additional paid provider.

## New real implementation

`src/devhub/intelligence/codeforge_host_binding.py` exposes
`verify_with_host(request, branch_fetch=..., file_fetch=...)`.
The authorized host supplies the actual **read-only** GitHub functions:

- `mcp__GitHub__fetch({url: ...})` for branch HEAD;
- `mcp__GitHub__fetch_file({repository_full_name, path, ref})` for the immutable file readback.

The adapter validates the exact five-field request through the existing R11 contract *before* invoking a handle, reuses the R11 byte-verified SHA-1 blob comparison, and fetches the branch twice. A registered repository mapping is fixed in 666DEV code: a proposal cannot select arbitrary URLs or foreign write handles.

R12 returns source metadata and hashes only, not the peer body. The provider is never discovered, connected, or invoked automatically. There is **no** general-purpose executor or arbitrary remote code call. Foreign embedded triggers remain inert. A missing handle is `READBACK_PENDING`; invalid peer identity/path is `CONFLICT_QUARANTINE`.

`src/devhub/intelligence/operations.py` exposes the new read-only host binding contract under the existing Operations Center, preserving exactly seven native facets and `provider_host_verified=false` until actual external execution can be independently demonstrated.

## Tests and evidence limits

`tests/test_codeforge_host_binding_r12.py` verifies injected mocked GitHub host responses, changed branch, forged blob, absent handles, unregistered peers, inert external instructions and protection from implicit writes.

A passing CI run proves the source adapter and mock-bound contracts, **not** that the installed LYVRA Coding Profi, Coder or any other independent plugin has dispatched a real host job. A live host must inject its actual provider function handles, execute this exact module at a pinned 666DEV commit, and return an independently verifiable provider invocation receipt. Only then may the host acceptance status advance.

R12 is a 666DEV development candidate; productive `666DEV` branch and Current are not automatically changed. Legacy historical Git object and Windows-host security gates remain independent and open.
