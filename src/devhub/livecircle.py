"""Portable continuation records derived from the native 666DEV state."""
from __future__ import annotations

import hashlib
import json

from . import core

KIND = "666dev-livecircle"
VERSION = 1
ACTIONS = ("LIVECIRCLE", "REHYDRATE", "NEW-CHAT", "NEXT-CHAT")


def snapshot(project_id: str) -> dict:
    profile, _ = core.project_profile(project_id)
    record = {
        "kind": KIND,
        "schema_version": VERSION,
        "authority": "666DEV",
        "hub_commit": core.git(core.ROOT, "rev-parse", "--verify", "HEAD^{commit}"),
        "project_id": project_id,
        "profile_path": core.project_entries()[project_id],
        "source_mode": profile["source_mode"],
        "profile_sha256": hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
        "source_commit": None,
        "working_tree_clean": None,
        "working": None,
        "current": None,
        "return_anchor": None,
        "next_action": None,
        "status": "READBACK_PENDING",
    }
    try:
        state = core.rehydrate(project_id, initialize_demo=False)
    except core.DevhubError as exc:
        reason = str(exc).lower()
        if any(word in reason for word in ("checkpoint", "state pointer", "quarantined")):
            record["status"] = "CONFLICT_QUARANTINE"
        return record

    view = core.inspect_project(project_id, state=state)
    record["source_commit"] = view["commit"]
    record["working_tree_clean"] = core.clean_source(state["source"])
    for name in ("working", "current"):
        if state[name]:
            pointer = state[name]["pointer"]
            record[name] = {key: pointer[key] for key in ("checkpoint_id", "commit", "sha256")}
    if state["working"]:
        record["return_anchor"] = state["working"]["checkpoint"].get("return_anchor")
    record["status"] = view["revision_status"]
    if state["working"]:
        results = state["working"]["checkpoint"]["results"]
        record["evidence"] = {
            "total": len(results),
            "at_source_commit": sum(item.get("commit") == view["commit"] for item in results),
        }
    if not record["working_tree_clean"]:
        record["status"] = "PARTIAL"
    else:
        record["next_action"] = view["next_action"]
    return record


def resume(project_id: str, handoff: dict) -> dict:
    """Compare a handoff with live state. Never apply data from the handoff."""
    if (not isinstance(handoff, dict) or handoff.get("kind") != KIND
            or type(handoff.get("schema_version")) is not int or handoff["schema_version"] != VERSION):
        raise core.DevhubError("Ungültiges 666DEV-Handoff-Format.")
    if handoff.get("authority") != "666DEV" or handoff.get("project_id") != project_id:
        return {"status": "CONFLICT_QUARANTINE", "reason": "Projekt oder Autorität stimmt nicht überein."}
    current = snapshot(project_id)
    if current["status"] in {"READBACK_PENDING", "CONFLICT_QUARANTINE"}:
        return {"status": current["status"], "livecircle": current}
    keys = ("hub_commit", "profile_path", "profile_sha256", "source_mode", "source_commit", "working", "current", "return_anchor")
    changes = [key for key in keys if handoff.get(key) != current[key]]
    if changes or handoff.get("working_tree_clean") is not True or not current["working_tree_clean"]:
        return {"status": "PARTIAL", "changed_fields": changes, "livecircle": current}
    return {"status": current["status"], "changed_fields": [], "livecircle": current}
