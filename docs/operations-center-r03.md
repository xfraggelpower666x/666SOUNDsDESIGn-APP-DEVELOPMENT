# 666DEV R03 · Causal revalidation and bounded outcome review

Authority: 666DEV native project profile, Git revision, LiveCircle and existing IMPACT.

## Adopted source modules

- `src/devhub/intelligence/causal_learning.py` is a **pure**, read-only candidate and causal planner, based on the prepared R03 overlay.
- `tests/test_causal_learning_r03.py` tests recheck chains, uncertain impact, revision mismatch, contradictory observations and promotion lock.
- CLI: `666DEV <PROJECT-ID> CAUSAL [BASE]`. This invokes native `project_impact` then computes `plan_revalidation`. Missing native source/unsafe state returns READBACK_PENDING.
- Windows Control: the existing control panel exposes **Kausale Testprüfung (R03)** via its existing loopback action route. It does not add write powers.

## Evidenzregeln

The causal plan is derived from native impact data: `ABGELEITET` never means that tests were rerun. `UNIMPACTED` is scoped to the verified difference and does not certify a previous test receipt. Unknown paths, changed inventories and unresolved graph diagnostics require precautionary rechecks.

`review_outcome` classifies a scoped, falsifiable learning candidate using *caller-provided* observations. These are not authenticated proofs. Contradictions remain visible, independent verification stays OFFEN, `promotion=FORBIDDEN` and `learning_state_changed=False`.

No persistent learned rules, native project Current writes, automatic repair, deployment or foreign-system activation are part of R03.

## Host and release gates

GitHub CI establishes repository regression only; it does not establish Windows .cmd, browser click-path, production host or native ChatGPT plugin execution acceptance. Plugin release requires a separately verified source update. No production project or facet checkpoint is manufactured during integration.

## Next

- Add independently verified receipts for outcome decisions.
- Add explicit scope-approved learned state only once a separate policy and migration are reviewed.
- Verify Windows keyboard, browser, .cmd and plugin-host behavior in their actual hosts.

## R03 plugin parity · 2026-11-20

- `666dev-coding-control` release `0.1.9`, ID `pluginrel_6b00ca6eca6481918f00b75c320521f6`.
- Provider readback: both plugin manifests `0.1.9`, R03 Operations Center skill, original LiveCircle skill retained, 43 keywords retained.
- GitHub repository implementation was verified at commit `531be27232d6eda9a8738691d00cd63f945d8aec`; workflow `666DEV verify` run `44829667821` completed successfully.
- Plugin source publication `VERIFIZIERT`; plugin host behavior and native Windows CMD/click-path remain `OFFEN`.
- No productive project Current, facet checkpoint or learning rule was created or promoted.
