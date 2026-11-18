"""Derive read-only recovery decisions from the verified LiveCircle snapshot."""
from __future__ import annotations

import hashlib
import json
import sys

PROFILE_FIELDS = ("profile_path", "profile_sha256", "source_mode")
NATIVE_ACTIONS = {"SYSTEMSTART", "STATUS", "WEITER", "CODEFORGE"}


def profile_fingerprint(profile: dict) -> str:
    return hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()


def command_display(command: str | list[str]) -> str:
    return command if isinstance(command, str) else json.dumps(command, ensure_ascii=False)


def summarize_acceptance(profile: dict, revision: str, results: list[dict], *,
                         clean: bool) -> dict:
    """Use only matching native receipts, separating execution from the verdict."""
    fingerprint = profile_fingerprint(profile)
    latest = {}
    for result in results:
        execution = result.get("execution")
        if not isinstance(execution, dict) or result.get("commit") != revision:
            continue
        if execution.get("profile_sha256") != fingerprint or execution.get("platform") != sys.platform:
            continue
        kind = result.get("evidence_type")
        source = result.get("source")
        if not isinstance(source, str):
            continue
        if kind == "test" and clean and execution.get("source_kind") == "checkout" and execution.get("clean_revision") is True:
            latest[(kind, source)] = execution
        elif kind == "build" and execution.get("source_kind") == "committed_copy":
            latest[(kind, source)] = execution

    summary = {}
    for kind in ("test", "build"):
        counts = dict(passed=0, failed=0, blocked=0, pending=0)
        issues = []
        for position, command in enumerate(profile.get(f"{kind}_commands", []), start=1):
            receipt = latest.get((kind, command_display(command)))
            if receipt is None:
                counts["pending"] += 1
            elif receipt.get("state") != "completed" or type(receipt.get("exit_code")) is not int:
                counts["blocked"] += 1
                issues.append({"command_index": position, "state": receipt.get("state") or "unknown", "exit_code": None})
            elif receipt["exit_code"] == 0:
                counts["passed"] += 1
            else:
                counts["failed"] += 1
                issues.append({"command_index": position, "state": "completed", "exit_code": receipt["exit_code"]})
        summary[kind] = {**counts, "issues": issues}
    return summary


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
    acceptance = current.get("acceptance", {})
    project = {"state": "NATIVE_STEP_AVAILABLE", "evidence": evidence}
    if any(counts["failed"] or counts["blocked"] for counts in acceptance.values()):
        project["state"] = "DIAGNOSE_ACCEPTANCE"
        project["inspection_command"] = [*project_command, "STATUS"]
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
