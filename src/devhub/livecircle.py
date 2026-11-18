"""Portable continuation records derived from the native 666DEV state."""
from __future__ import annotations

import hashlib
import json
import re

from . import core
from .desktop_impact import desktop_impact

KIND = "666dev-livecircle"
VERSION = 1
ACTIONS = ("LIVECIRCLE", "REHYDRATE", "NEW-CHAT", "NEXT-CHAT")


def snapshot(project_id: str, *, desktop_base: str | None = None) -> dict:
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
    record["desktop_impact"] = desktop_impact(core.ROOT, record["hub_commit"], desktop_base)
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


def resume(project_id: str, handoff: dict, *, observed: dict | None = None) -> dict:
    """Compare a handoff with live state. Never apply data from the handoff."""
    if (not isinstance(handoff, dict) or handoff.get("kind") != KIND
            or type(handoff.get("schema_version")) is not int or handoff["schema_version"] != VERSION):
        raise core.DevhubError("Ungültiges 666DEV-Handoff-Format.")
    if handoff.get("authority") != "666DEV" or handoff.get("project_id") != project_id:
        return {"status": "CONFLICT_QUARANTINE", "reason": "Projekt oder Autorität stimmt nicht überein."}
    current = snapshot(project_id) if observed is None else observed
    old_hub = handoff.get("hub_commit")
    if (current["desktop_impact"]["basis"] == "FIRST_PARENT" and isinstance(old_hub, str)
            and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", old_hub) and old_hub != current["hub_commit"]):
        current = {**current, "desktop_impact": desktop_impact(core.ROOT, current["hub_commit"], old_hub)}
    if current["status"] in {"READBACK_PENDING", "CONFLICT_QUARANTINE"}:
        return {"status": current["status"], "livecircle": current}
    keys = ("hub_commit", "profile_path", "profile_sha256", "source_mode", "source_commit", "working", "current", "return_anchor")
    changes = [key for key in keys if handoff.get(key) != current[key]]
    if changes or handoff.get("working_tree_clean") is not True or not current["working_tree_clean"]:
        return {"status": "PARTIAL", "changed_fields": changes, "livecircle": current}
    return {"status": current["status"], "changed_fields": [], "livecircle": current}


def hub_entry(*, update: bool = False) -> dict:
    """Read the hub registry without selecting a project or creating a checkpoint."""
    action = "UPDATE" if update else "SYSTEMSTART"
    head = core.git(core.ROOT, "rev-parse", "--verify", "HEAD^{commit}")
    return {
        "authority": "666DEV",
        "action": action,
        "status": "PROJECT_SELECTION_REQUIRED" if update else "PARTIAL",
        "hub_commit": head,
        "desktop_impact": desktop_impact(core.ROOT, head),
        "project_id": None,
        "projects": sorted(core.project_entries()),
        "project_status": "OFFEN",
        "next_command": f"666DEV <PROJEKT-ID> {action}",
    }


def diagnose(project_id: str | None = None, handoff: dict | None = None) -> dict:
    """Report checkable authority and state drift. Host behavior needs chat evidence."""
    if project_id is None:
        return {
            **hub_entry(),
            "action": "FUCK HORST",
            "status": "READBACK_PENDING",
            "reason": "Kein Projekt für den Quellen- und Scope-Abgleich gebunden.",
            "next_command": "666DEV <PROJEKT-ID> FUCK HORST",
        }

    observed = snapshot(project_id)
    result = {
        "authority": "666DEV",
        "action": "FUCK HORST",
        "check_scope": "Quellenrevision, Profil, Working und Current",
        "livecircle": observed,
    }
    if observed["status"] in {"READBACK_PENDING", "OFFEN"}:
        return {**result, "status": "READBACK_PENDING", "reason": "Projektzustand nicht vollständig belegt."}
    if observed["status"] == "CONFLICT_QUARANTINE":
        return {**result, "status": "OBSERVED_DRIFT", "reason": "Nativer Pointer- oder Checkpoint-Konflikt."}
    if handoff is not None:
        comparison = resume(project_id, handoff, observed=observed)
        if comparison["status"] == "CONFLICT_QUARANTINE":
            return {**result, "status": "OBSERVED_DRIFT", "reason": comparison["reason"]}
        if comparison.get("changed_fields"):
            return {**result, "status": "SUSPECTED_DRIFT", "changed_fields": comparison["changed_fields"],
                    "reason": "Abweichende Übergabebasis. Prüfe die Herkunft und neuere gültige Entwicklung."}
        if comparison["status"] == "PARTIAL":
            return {**result, "status": "SUSPECTED_DRIFT", "reason": "Übergabe oder nativer Stand unvollständig."}
    if observed["status"] == "PARTIAL":
        return {**result, "status": "SUSPECTED_DRIFT", "reason": "Lokaler Diff oder ältere Checkpoint-Basis."}
    return {**result, "status": "NO_DRIFT_EVIDENCE"}
