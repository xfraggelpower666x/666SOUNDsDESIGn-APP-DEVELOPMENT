# 666DEV R10 · Executable CodeForge Cooperation

**Owner:** 666DEV · Source of Current: the productive 666DEV branch and the native project LiveCircle.
**Method lead:** LYVRA Coding Profi, advisory-only. No peer plugin or foreign repository receives 666DEV credentials, Current, or implicit execution authority.

R10 extends the **existing** R09 plan and native 666DEV `apply_candidate()` worktree mechanism; it does not create a second CodeForge, LiveCircle, global router, authority layer, or eighth facet.

## 1. Planned vs. executable

`666DEV CODEFORGE-TEAM PLAN <proposal.json>` is a source-bound review. Its result
`PLAN_READY_NOT_DISPATCHED` means a valid *plan*, not execution.

`666DEV CODEFORGE-TEAM EXECUTE <proposal.json> <workstream-id> <candidate-relative> <exact-sha256>`
is an **explicit direct invocation** of 666DEV's native local executor. It accepts
only the first eligible wave, a 666DEV-owned workstream with `VERIFIZIERT`
evidence, matching native project ID, source HEAD and immutable candidate
digest. Peer identities, missing dependencies, stale SHA, unapproved paths,
duplicate execution and changed project source fail closed.

The `candidate-relative` path points under the project's
`state/patch-candidates/`, **not** to an arbitrary file or outside repo.
Candidate schema/version and `status=VORGESCHLAGEN` are required.

A successful action makes a **detached isolated Git worktree** using the existing
`apply_candidate()`, checks the exact changed-file set, reads every resulting
file back against the approved candidate content, runs `git diff --check`,
rechecks native source HEAD and clean status, and executes only the existing
profile-declared **build** commands through the native 0-EUR Cost Guard.
Unknown-cost commands are blocked. A receipt with the per-file SHA-256,
candidate digest, revision, worktree path and actual build evidence is stored
under the ignored `.work/codeforge-receipts/<project-id>/`.

**Important:** Successful local syntax compilation is not the full project
test suite. `tests_verified=false`, `github_write_verified=false`,
`plugin_host_verified=false`, and `current_updated=false` remain explicit.
`PARTIAL` does not imply completed acceptance.

## 2. Controlled GitHub write — draft PR only

`666DEV CODEFORGE-TEAM DRAFT-PR <project-id> <receipt-id> <base-commit> <target-branch> CONFIRM_DRAFT_PR`

This is a *separate, explicit* native action requiring Git and GitHub CLI with
owner authorization. It reads the recorded isolated worktree, verifies exact
file hashes and detached source commit, profile ownership (`monorepo` only),
the pinned 666DEV remote, target ref matching the immutable base commit,
absence of an existing draft branch, and a public GitHub repository before
allowing a zero-cost standard GitHub Git/PR API operation. It stages only the
receipt-approved paths, commits them on the isolated candidate, pushes a
new `666codeforge/r10-<receipt-id>` branch and creates a **draft** PR.
It never uses `--force`, changes Current, merges PRs, modifies foreign repos,
or consumes any paid credit. Missing GitHub CLI/credentials/host acceptance
block actual publication; the mere presence of this code is no host proof.

After creation, GitHub remote branch HEAD, draft PR HEAD/base and unchanged
target base are independently read back. A separate `DRAFT_<receipt-id>.json`
receipt records the resulting status. PR CI, plugin/Windows-host acceptance and
release promotion remain independent gates. A remote push with failed
post-push readback is `READBACK_PENDING` and must be reconciled before retry;
never retry blindly or overwrite an existing branch.

## 3. Cross-repository specialization

LYVRA Coding Profi leads *methods, review and prioritization*, not owner
credentials, GitHub mutation, or project Current. CLIC, LYVRA SuperCodeForge,
666MAIN BRAIN, Coder and other peers may submit provenance-bound proposals.
Their native owners must explicitly authorize and execute changes on their
own repositories, followed by native regression/readback and a receiver
return receipt. R10 does not pretend to dispatch connected plugins or provide
cross-system host handles.

## 4. Regression and release conditions

- `tests/test_codeforge_execution_r10.py` exercises a **real local Git
  repository, isolated worktree, approved source patch, zero-cost Python
  compilation and JSON receipt readback** plus invalid SHA/foreign peer/path.
- `tests/test_codeforge_publication_r10.py` covers approval, native ownership,
  SHA, modified files, private repo block and simulated GitHub draft PR
  CAS/readback (simulation is not a real GitHub PR).
- GitHub CI exercises the native regression in the repo's existing workflow.
- SOURCE, LOCAL TEST, CI, DELIVERY, ADOPTION and HOST remain separate.
- Productive Current pointer stays untouched; previous R08 security hold on
  historical exposed Git object remains and is not waived by R10 CI success.
