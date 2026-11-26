# 666DEV R14.1 — Host-Receipt CAS/Concurrency Repair

Native source: `xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT`
Base: `cdadfde705c5b1587b8be43c81615ace403ef340`
Authority: 666DEV only. Release candidate; no productive Current change.

## Confirmed source gaps

The previous R14 receipt code validated HEAD/module SHA only **before**
provider calls and checked duplicate receipts without an execution lock.
Two callers could therefore invoke the same provider concurrently before
either wrote a receipt; a source revision change during external reads could
also be missed. Provider callback exceptions were not converted into a
sanitized, pending receipt.

## Minimal changes

- Acquire a per-execution, SHA-bound `.lock` with exclusive O_EXCL semantics
  **before** invoking the injected host callbacks. Another concurrent caller
  receives `CONFLICT_QUARANTINE`, no provider calls. The lock is released
  in `finally`; existing receipts retain the no-replay behavior.
- Re-read the native Git HEAD and actual R12 Python module blob **after**
  callbacks and before writing the receipt. Any drift is quarantined and
  no receipt is published.
- Exceptions from injected providers are safely represented as
  `READBACK_PENDING` without copying exception text or secrets.
- Preserve `CONFLICT_QUARANTINE` from invalid peer source requests instead
  of silently converting it to a generic pending state.
- Preserve all seven facets, the existing R09–R14 APIs and the exact original
  R12 adapter call. No foreign writes, no Current mutation, no new runtime.

New regression file:
`tests/test_codeforge_host_cas_r141.py`

## Evidence limits

This repair improves local host-call correctness. It **does not** make a
callable test double into a trusted ChatGPT plugin runtime. Real plugin
host identity and connector-host provenance cannot be inferred from GitHub
CI or a self-described receipt. Until an independent host executes the
original adapter with its actual authorized handles and supplies a verified
execution attestation, `chatgpt_plugin_host_verified=false`,
`github_connector_host_verified=false`, `READBACK_PENDING` for host
acceptance.

Existing historical security HOLD, Windows GUI acceptance and production
promotion remain separate. No paid integrations.
