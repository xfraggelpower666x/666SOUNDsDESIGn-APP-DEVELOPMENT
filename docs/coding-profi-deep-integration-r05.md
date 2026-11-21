# 666DEV R05 — Coding Profi v0.87.0 Deep Integration Audit

Source: user-supplied `L.Y.V.R.A. CODING PROFI (6).zip`, SHA-256 `bead8f813e76422359dc91c9c84f7e20bddf74c42fc30727c2c121a674da1861`, 260 files / 135 source skills / 51 top-level references.
Native baseline: productive `666DEV` commit `5c16f59aa64a61c94d8d93bca15e3e9f4128fb3d`.
Plugin baseline: `666dev-coding-control` v0.2.1, release `pluginrel_6b0145412fec819189e7a89b846b11eb`, 313 files / 138 skill registrations.

## Evidence methodology and limitations

All 135 source skill names were crosschecked against the installed 666DEV plugin. Every one is present. The 135 skill bodies were compared by nonempty original-line inclusion against the installed matching target skill, ignoring the target's 666DEV authority wrapper. **119/135 retain all compared nonempty original lines**, while **16/135 have at least one changed or absent line**. This is *textual* coverage of the skill definitions, not end-to-end functional parity, repository source validity or host execution evidence. Import references under `references/coding-profi-v087-source/` are provenance only, never native authority.

Changed-line review (approximate original-line coverage): app-code .97; agentenlauf-chat .92; code-assistant .99; code-converter .62; code-engineering .91; coding-profi-chat .95; coding-profi-livecircle .09 (deliberate DEV-native redirect); electron .91; powershell-scripting .81; research .90; scevi-visual-intelligence .79; self-healing .80; testing .95; windows-batch-build .75; windows-projektstarter .93; toolstarter-coding .80.

Retained specialist families include: NLP/semantics, causal/evidence/relational/emergence, code review and repair, parallel orchestration, Python/JS/Java/Go/Rust/.NET, source graph, testing, Intelligent UI, Visual Daemon, visual formats and PowerShell Git. The plugin source skills are methods; no Whole LYVRA state or foreign Current is adopted.

## Confirmed defect R05-NATIVE-01 — same-SHA stale NEXT-CHAT acceptance

**Entry:** `666DEV <project> CODING-PROFI NEW-CHAT` then `NEXT-CHAT`. **Origin:** `src/devhub/intelligence/coding_profi.py` before R05. Handoff identity checked the hub/source/profile source revision but not the native Working, Current or return anchor and not the facet digest. An unchanged Git commit with changed Working/Current pointers yielded `handoff_accepted=True` and `status=OFFEN`; `PARTIAL` also yielded accepted=true.

**Impact:** an obsolete task position could appear safely rehydrated. **Repair:** Include a `continuity_binding` covering native Working/Current/return anchor, facet checkpoint status/digest; include bounded, verified `work_context` (return anchor, last verified step, obligations, evidence IDs). Reject changed binding or work context with `CONFLICT_QUARANTINE`; old handoffs without new binding become `READBACK_PENDING`. `PARTIAL` is not accepted. No native pointer or project contents are modified. `task_resumed` denotes only a matching verified facet record, never execution of a task.

**Regression:** 4 tests added in `tests/test_coding_profi_facet_r04.py`, including same-commit pointer changes, partial facet state, legacy handoff and scoped evidence drift. Focused local test: 15/15 successful. Full GitHub `666DEV verify` workflow must pass before native publication.

## Confirmed plugin gaps to remediate separately

1. `skills/sceeri-code-converter/SKILL.md` lacks the source's **.NET TRX case-by-case parity section**; the live plugin also lacks `scripts/compare_trx.py` and its test. Add source script + five original tests, restore an explicit routed contract while retaining existing DEV-specific guidance.
2. Public `references/windows-starten-build.md` referenced by source Windows skills is missing at plugin root (the newer source file exists in archival `references/coding-profi-v087-source/`). Restore the root route, read-only; do not launch installers from a skill.
3. Original Coding-Profi LiveCircle is intentionally redirected to native 666DEV. Preserve its *continuity semantics*, not its foreign storage or execution authority; the R05 fix resolves the confirmed handoff gap. Full user-facing task/line and decision survival requires separate host tests and verified evidence.
4. `sceeri-self-healing`, `sceeri-research`, `sceeri-scevi-visual-intelligence`, `toolstarter-coding` and Windows specialist skills have source-version additions not identical to the target versions. Add non-destructive specialist guidance only where the missing behavior is clearly evidenced; retain newer 666DEV-native security gates. Do not automatically upgrade ToolStarter binary/runtime or modify Windows control based on text differences.

## Native boundaries / release requirements

Native 666DEV GitHub + selected project profile and native LiveCircle remain sole authority. The R03 causal planner is read-only; candidate learning is not a verified, persistent learned rule. External plugin publication != native CI != Windows host acceptance. Production release requires prechange backup, source and tests, GitHub CI, direct readback and pointer-last; remote plugin release requires its own provider readback. No production Project Current was inferred or written. This document is evidence, not a new trigger or execution permission.
