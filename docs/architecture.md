# 666DEV architecture and evidence

## Ownership

`registry/projects.json` maps an ID to one profile. `projects/<id>/project.json`
defines its source mode, expected ref, declared entry points, build/test contracts,
write scope and acceptance conditions. A monorepo source is below this repository;
a linked source remains in its own local Git checkout. Local checkout paths are stored
only in ignored `.work/config.json`.

Current references and immutable checkpoints are written below the selected project's
`state/`. The checkpoint is written and hashed before the Current pointer is updated
under a project lock. The pointer is compared with its original value immediately
before replacement and read back afterward. A conflict leaves Current unchanged.
Ignored `.work/` contains locks, linked demo checkout, isolated worktrees, freezes,
and temporary dashboard data.

## Evidence and statuses

An evidence result has a status, evidence type, source path or command, Git commit,
environment and observed output. Supported status names are:

`VERIFIZIERT`, `ABGELEITET`, `VORGESCHLAGEN`, `OFFEN`, `BLOCKIERT`, `PARTIAL`,
`WRITE_BLOCKED`, `READBACK_PENDING`, and `CONFLICT_QUARANTINE`.

The Python adapter parses imports using `ast`; the packaging adapter reads declared
TOML console scripts and links entry points, target modules, build contracts and
profiled tests. Dynamic import resolution stays `OFFEN`. Graph edges record direction,
revision, source and evidence level. Changes to another project are never written by
the selected project's workflow.

`LocalGitProvider` performs local read-only commit, file and blob reads. Protocols
describe future GitHub, CI and target-host readback; those providers are not
implemented. Their states are surfaced as `READBACK_PENDING` or `OFFEN`.

## Verification

`python -m devhub.verifier --base <commit>` is the common local/CI verifier entry.
Without `--base`, commit-diff scope is skipped and the result is `PARTIAL`. Checkpoint
hashes are SHA-256 over the serialized checkpoint bytes. Freeze manifests map archive
relative paths to SHA-256 digests; ZIP extraction paths are checked against traversal.

The dashboard loads generated `dashboard.json` as data and binds locally on
`127.0.0.1`. It has no command execution endpoint. Repository text is inserted using
DOM text nodes, not HTML interpretation.

## Demonstrations

`demo-monorepo` has its application and packaging contract in this repository.
`demo-linked` is a fixture initialized as a separate, local Git repository with a real
commit and `main` ref; its checkout is generated only under `.work/`.
