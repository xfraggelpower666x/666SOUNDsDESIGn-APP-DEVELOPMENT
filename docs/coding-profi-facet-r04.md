# 666DEV R04 · Coding Profi Intelligence Facet

Authority: **666DEV native GitHub branch and selected project**. External skill source: sceeri-intelligence/sceeri-coding-profi-chat and sceeri-coding-profi-livecircle; adapter copies no foreign runtime, identity, tokens or internal private skill assets.

## Existing architecture preserved

- New additive `coding-profi` facet in Operations Center and facet_store `FACET_IDS`.
- Direct 666DEV CLI router `666DEV <PROJECT-ID> CODING-PROFI <ACTION>`.
- Read-only SYSTEMSTART, STATUS, LIVECIRCLE, WEITER, NEW-CHAT and NEXT-CHAT; explicit handoff file only for NEXT-CHAT.
- Project native LiveCircle snapshot is read freshly. Facet checkpoint is read through the existing R02 checkpoint store; no automatic SAVE.
- Handoff fields include exact project ID, authority and hub/source/profile binding; stale/foreign payloads are quarantined.
- WEITER suggests read-only CAUSAL or LIVECIRCLE commands; does not execute them.
- Host acceptance of the actual SCEERI plugin remains OFFEN. No LYVRA systemstart or cross-system merge.

## Separate uploaded Research Orchestra guard

`666_RESEARCH_ORCHESTRA_RECOVERY_GUARD_R01_READBACK_PENDING.zip` is a different native system's **non-restorable** partial recovery evidence with documented 126 missing historical hashed files. No source or trigger from this ZIP is promoted into 666DEV current. Its archive hygiene principles can be independently considered for a future optional read-only audit adapter after user authorization.

## Release gates

Production publication requires the exact native base, test and CI evidence, GitHub readback and pointer-last. The integration does not manufacture a project Current, claim external plugin host acceptance or execute foreign triggers.
