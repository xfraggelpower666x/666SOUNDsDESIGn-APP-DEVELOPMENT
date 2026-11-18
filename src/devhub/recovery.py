"""Derive read-only recovery decisions from the verified LiveCircle snapshot."""
from __future__ import annotations

PROFILE_FIELDS = ("profile_path", "profile_sha256", "source_mode")
NATIVE_ACTIONS = {"SYSTEMSTART", "STATUS", "WEITER", "CODEFORGE"}


def assess_recovery(status: str, current: dict | None = None, changes: list[str] | None = None,
                    *, previous_clean: bool = True) -> dict:
    if status in {"READBACK_PENDING", "CONFLICT_QUARANTINE"} or current is None:
        return {"context": {"state": status}, "project": {"state": status}}

    changed = changes or []
    project_id = current["project_id"]
    project_command = ["666DEV", project_id]
    context = {
        "state": "REBUILD_FROM_NATIVE" if changed or not previous_clean else "MATCHES_HANDOFF",
        "changed_fields": changed,
        "hub_commit": current["hub_commit"],
        "working": current["working"],
        "current": current["current"],
    }
    evidence = {
        "source_commit": current["source_commit"],
        "profile_sha256": current["profile_sha256"],
        "working_tree_clean": current["working_tree_clean"],
        "checks_at_source_commit": current.get("evidence", {}).get("at_source_commit"),
    }
    project = {"state": "NATIVE_STEP_AVAILABLE", "evidence": evidence}
    if (current["working_tree_clean"] is not True or "source_commit" in changed
            or any(field in changed for field in PROFILE_FIELDS)
            or current["status"] == "PARTIAL"):
        project.update(
            state="REVALIDATE_PROJECT",
            inspection_command=[*project_command, "IMPACT"],
        )
    action = current.get("next_action")
    if action in NATIVE_ACTIONS:
        project["native_next_command"] = [*project_command, action]
    return {"context": context, "project": project}
