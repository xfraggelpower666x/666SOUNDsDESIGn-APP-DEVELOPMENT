# 666DEV Security R07 — incident cleanup readback (2026-11-22)

Authority: 666DEV only. This is a nonsecret evidence report, not a Current pointer.

## Verified live observations

- Productive branch `666DEV` remained at `e1ef4abf5830bcd3ef477543e4a626f0c4835aff`.
- Bad historical Git commit: `2042890ed10568fd87f6deb756e7ec30dab31014`.
- Audit branch `audit/666dev-native-plugin-capability-parity-20261122`
  was observed pointing to the safe R05 commit, not the bad commit.
- Exposed recovery artifact `14733154164` from run `44970731875`
  was removed by one-time workflow run `45013493932`.
  Job output verified exact metadata, DELETE HTTP 204 and direct GET HTTP 404.
  The source run's artifact listing was rechecked and empty.
- Historical workflow run `44970731875` was removed by one-time
  workflow run `45013560935`. Job output verified run SHA and branch,
  confirmed zero attached artifacts, DELETE HTTP 204 and GET HTTP 404.
  A separate GitHub API read returned 404 for the deleted run.
- Both one-time workflows were removed from the security branch afterward.
  The standing `verify.yml` only creates/publishes new revision-bound recovery
  archives on a productive `666DEV` push; no feature or PR uploads.
- 666DEV's seven native Operations Center facets and installed private
  plugin sources were not changed by incident cleanup.
- GitHub standard `ubuntu-latest` on this public repo is free; no
  billed third-party automation or wallet credits were authorized.

## Explicitly not verified / security hold

- A direct fetch of historical commit `2042890ed10568fd87f6deb756e7ec30dab31014`
  **still succeeded after the original branch was reset**.
  Cleanup of GitHub object store, cached commit/diff views, hidden PR refs,
  independent clones/forks, and any secrets accidentally exposed is NOT proven.
- GitHub Support may be required for cache purging and dangling object
  dereferencing (see GitHub Docs: removing sensitive data from a repository).
- Full Windows-host and current private plugin-host acceptance are still OPEN.
- No production merge, Current pointer advancement, history rewrite, foreign
  system mutation, or private-source mirroring was performed.

## Release gates

Keep `SECURITY_HOLD` until contaminated Git object/cache refs are
independently resolved, affected credentials rotated if any, Windows and
plugin host acceptance is proven, and a fresh R07 regression/readback
is available. Preserve a clean R05 recovery anchor, audit native changes,
and publish native pointer last. Do not treat this incident log as a
license to import foreign authority or activate embedded triggers.
