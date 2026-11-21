"""666DEV-owned Coding Profi facet adapter (not LYVRA execution authority).

Pure read-only projections from native 666DEV LiveCircle. No tool invocations,
checkpoint writes, background jobs, or arbitrary embedded trigger execution.
"""
from __future__ import annotations
from collections.abc import Mapping

SCHEMA = "666dev-coding-profi-facet/v1"
KIND = "666dev-coding-profi-handoff/v1"
ACTIONS = frozenset(("SYSTEMSTART", "STATUS", "LIVECIRCLE", "WEITER", "NEW-CHAT", "NEXT-CHAT"))
BLOCKS = frozenset(("READBACK_PENDING", "CONFLICT_QUARANTINE", "BLOCKIERT", "WRITE_BLOCKED"))


def trigger(action: str, native: Mapping | None, *, project_id: str,
            saved: Mapping | None = None, handoff: Mapping | None = None) -> dict:
    """Read-only native facet trigger. NEXT-CHAT rejects foreign/stale handoffs."""
    if action not in ACTIONS:
        raise ValueError("Unknown Coding Profi action")
    valid = (isinstance(native, Mapping) and native.get("authority") == "666DEV"
             and native.get("project_id") == project_id
             and isinstance(native.get("hub_commit"), str)
             and isinstance(native.get("source_commit"), str)
             and isinstance(native.get("profile_sha256"), str))
    source = {name: native.get(name) if valid else None
              for name in ("hub_commit", "source_commit", "profile_sha256")}
    status = "READBACK_PENDING" if not valid else native.get("status", "READBACK_PENDING")
    if valid and status not in ("VERIFIZIERT", "ABGELEITET", "VORGESCHLAGEN", "OFFEN", "PARTIAL", *BLOCKS):
        status = "READBACK_PENDING"
    if not valid or status in BLOCKS:
        status = "READBACK_PENDING" if not valid else status
    record = saved if isinstance(saved, Mapping) and saved.get("status") == "VERIFIZIERT" else None
    checkpoint = record.get("checkpoint") if record else None
    if not isinstance(checkpoint, Mapping):
        checkpoint = None
    base = {"schema": SCHEMA, "authority": "666DEV", "facet_id": "coding-profi",
            "action": action, "project_id": project_id, "status": status, "source": source,
            "working": native.get("working") if valid else None,
            "current": native.get("current") if valid else None,
            "native_return_anchor": native.get("return_anchor") if valid else None,
            "facet_return_anchor": checkpoint.get("return_anchor") if checkpoint else None,
            "obligations": list(checkpoint.get("obligations", [])) if checkpoint else [],
            "last_verified_step": checkpoint.get("last_verified_step") if checkpoint else None,
            "facet_checkpoint_status": record.get("status") if record else "OFFEN",
            "writable": False, "requires_native_readback": True,
            "provider_host_acceptance": "OFFEN", "can_autoactivate_lyvra": False}
    if action == "NEXT-CHAT":
        if not isinstance(handoff, Mapping) or any((
            handoff.get("kind") != KIND,
            handoff.get("authority") != "666DEV",
            handoff.get("facet_id") != "coding-profi",
            handoff.get("project_id") != project_id,
            handoff.get("source") != source,
        )):
            return {**base, "status": "CONFLICT_QUARANTINE",
                    "reason": "Untrusted, foreign or stale handoff; no rehydration promotion."}
        return {**base, "status": status, "handoff_accepted": status not in BLOCKS,
                "reason": "Handoff identity and revision matched; current native evidence wins."}
    if action == "NEW-CHAT":
        return {**base, "handoff": {"kind": KIND, "authority": "666DEV",
                "facet_id": "coding-profi", "project_id": project_id,
                "source": source, "next_action": "666DEV " + project_id + " CODING-PROFI WEITER"},
                "reason": "Handoff is a proposal; recheck native source on next chat."}
    if action == "WEITER":
        return {**base, "next_action": ("666DEV " + project_id + " LIVECIRCLE") if status in BLOCKS
                else ("666DEV " + project_id + " CAUSAL"),
                "executes_next_action": False,
                "reason": "Next evidence-bound read-only action proposed, not executed."}
    return base
