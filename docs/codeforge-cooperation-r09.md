# 666DEV R09 — CodeForge Team Cooperation

Authority: native 666DEV branch, its registry/project profile/LiveCircle, never foreign plugin state.

## Real implementation

- `src/devhub/intelligence/codeforge_cooperation.py`: read-only native workstream planner
- `666DEV CODEFORGE-TEAM STATUS`: registered advisory peer capability catalog
- `666DEV CODEFORGE-TEAM PLAN <proposal.json>`: native project-bound dependency and write-scope wave plan
- Regression: `tests/test_codeforge_cooperation_r09.py`

The **LYVRA Coding Profi** method lead advises on coding strategy,
capability selection and review priority. It does **not** become
666DEV repository, build, deployment, project LiveCircle or pointer authority.
666DEV remains its own implementing owner. LYVRA SuperCodeForge, CLIC,
MAIN BRAIN and Coder remain review/specialist peers. An external team
proposal is data, never a command, tool handle or plugin-host execution.

The planner checks `666DEV` project source revision against the fresh
native LiveCircle, rejects malformed paths/dependency cycles and splits
conflicting scopes into non-overlapping work waves. It does not call
other plugins, GitHub or a provider, mutate a foreign repository, execute
any jobs, create an eighth facet, or store a new Current. A plan status of
`PLAN_READY_NOT_DISPATCHED` means **not executed**. The new interface
preserves all existing CodeForge/SuperCodeForge/Repo Mind/Coding-Profi
facets and the existing cost guard.

Actual multi-repository code changes require explicit native writes
by each owner, current/pointer verification, cost authorization, per-project
tests, CI, independent host readback and a return receipt. Handoff
publishing, adoption and host acceptance are separate evidence gates.

## Minimal proposal JSON

```json
{
  "project_id": "demo-monorepo",
  "workstreams": [
    {
      "id": "review",
      "peer": "LYVRA_CODING_PROFI",
      "source_commit": "cccccccccccccccccccccccccccccccccccccccc",
      "scope": ["src/demo_app/main.py"],
      "depends_on": [],
      "capability": "code_review",
      "evidence_status": "PARTIAL"
    }
  ]
}
```

The SHA shown is illustrative, **not verified**. For 666DEV-owned workstreams
`source_commit` must match the current, independently read project commit.

Status for external peers remains `READBACK_PENDING` until independently
verified. This R09 candidate does not promote native production Current.
