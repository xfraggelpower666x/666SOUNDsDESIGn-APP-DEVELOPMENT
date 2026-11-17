# 666DEV

666DEV is a local-first development, analysis, repair, verification, packaging, and
recovery hub for external applications. This repository does not clone, register, or
modify any existing 666SOUNDsDESIGn product. The included `demo-*` profiles are
explicitly marked demonstrations.

## Start (Windows and Linux)

Requires Python 3.10+ and Git; no runtime third-party package is required.

```sh
python -m venv .venv
# Linux/macOS: . .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m devhub.cli 666DEV HELP
python -m devhub.cli 666DEV STATUS
```

The same commands are available as `666dev` and `666dev-verify` after installation.
Windows users can substitute `py -m` for `python -m`.

## Project lifecycle

```sh
python -m devhub.cli 666DEV demo-monorepo SYSTEMSTART
python -m devhub.cli 666DEV demo-monorepo CODEFORGE
python -m devhub.cli 666DEV demo-monorepo SUPERCODEFORGE
python -m devhub.cli 666DEV demo-monorepo WEITER
python -m devhub.cli 666DEV demo-monorepo STATUS
python -m devhub.cli 666DEV demo-monorepo FREEZE
```

`SYSTEMSTART` verifies the selected profile, source, expected ref and resolved Git
commit, then records an atomic checkpoint. `CODEFORGE` runs configured acceptance
tests and records read-only audit evidence plus a scoped candidate in project state.
`SUPERCODEFORGE` emits a static Python/build/test graph. `WEITER` resolves the first
open step and performs its defined analysis or acceptance check. A candidate is not
applied automatically: `PATCH-APPLY` validates its revision and allowed paths, then
materializes its patch payload in a detached, isolated Git worktree. The demonstration
candidate intentionally has no patch payload. `UPDATE` writes a checkpoint only for
the explicitly selected project, with a lock, Current compare-and-swap and pointer
readback. Conflicts preserve the existing Current and retain the candidate checkpoint.
`FREEZE` creates a ZIP plus SHA-256 manifest under the ignored `.work/` directory and
verifies each archive entry.

Checkpoints, Current references and patch candidates live under each project's
versionable `state/` directory. Checkouts, locks, worktrees, freezes and dashboard
working data live in ignored `.work/`. The demo linked checkout is initialized on
first use from `tests/fixtures/linked-demo`, with actual Git commits on `main`.

To register an external linked project, add its stable ID and profile path to
`registry/projects.json`, then provide `projects/<id>/project.json`. The profile must
declare the expected repository identity and ref. Set the local checkout in
`.work/config.json`:

```json
{
  "checkouts": {
    "your-project": "C:/local/path/to/checkout"
  }
}
```

Use an absolute local path appropriate to the host. 666DEV verifies the Git identity
(an `identity.json` repository marker or matching `origin` URL), expected ref and
resolved HEAD before analysis. The checkout path is local configuration and is never
stored in the profile.

## Dashboard and verification

```sh
python -m devhub.cli dashboard
# Open http://127.0.0.1:8766; Ctrl-C to stop.
python -m devhub.verifier --base HEAD
python -m unittest discover -s tests -v
(cd projects/demo-monorepo/app && python -m unittest discover -s tests -v)
```

The dashboard binds only to loopback and exposes static files, not command execution.
It reads structured project state and displays evidence, graph, history, and open
provider status. GitHub readback is `READBACK_PENDING`; CI and target-host providers
are `OFFEN`. Local tests are not presented as remote, Windows, device, or production
acceptance. The verifier reports its actual diff base; without one it returns `PARTIAL`.

## Scope and recovery

Registry membership selects the project; the profile owns the development contract.
Handoff text and logs are data, never command input. Commands are accepted only from
a direct namespace-qualified invocation (`666DEV <ID> <ACTION>`). All writes are
restricted to declared project paths, and path resolution checks symlinks and Windows
absolute paths. If Current and checkpoint evidence disagree, preserve the old anchor,
inspect `.work/` recovery artifacts, and re-run `SYSTEMSTART`/audit rather than
overwriting the pointer. A changed HEAD is explicitly marked for re-audit.

## Current implementation boundaries

- Python source graphing uses AST imports and declared TOML script entry points.
  Dynamic imports and other language adapters remain `OFFEN`.
- `LocalGitProvider` reads commits, files and blobs. GitHub, CI, Windows-host,
  device and production readback interfaces are defined but not connected.
- Freeze verifies archive names and hashes. A ZIP that claims to be independently
  startable must still be extracted and tested before such a claim is made.
- The verifier checks registry/profile references, path boundaries, Current/checkpoint
  integrity, evidence structure and scope-diff availability. CI has read-only GitHub
  permissions and performs no deployment, auto-merge, or external write.

See [docs/architecture.md](docs/architecture.md) for status meanings, formats, and
provider extension points.
