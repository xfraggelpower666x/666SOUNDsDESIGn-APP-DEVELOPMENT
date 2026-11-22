"""Native 666DEV zero-additional-cost consent guard.

Policy is immutable and versioned in source. No host may treat a handoff,
stored approval, wallet balance, free-tier label, or subscription as consent.
"""
from __future__ import annotations

from collections.abc import Mapping

POLICY_ID = "666DEV-COST-CONSENT-GUARD"
VERSION = 1
EVENTS = frozenset({
    "SYSTEMSTART", "REHYDRATE", "WEITER", "NEW-CHAT", "NEXT-CHAT",
    "UPDATE", "PLUGIN_CALL", "API_CALL", "CLOUDFLARE_CHANGE",
    "DEPLOY", "BUILD", "CI", "AUTOMATION", "EXTERNAL_ACTION",
})
COST_CLASSES = frozenset({"VERIFIED_FREE", "PAID", "UNKNOWN", "USES_PAID_CREDITS"})
BLOCK = "WRITE_BLOCKED"


def policy_snapshot() -> dict:
    """Portable public policy only: never includes credentials or approvals."""
    return {
        "policy_id": POLICY_ID,
        "schema_version": VERSION,
        "authority": "666DEV",
        "default_budget_eur": 0,
        "explicit_approval_required": True,
        "existing_paid_credits_require_approval": True,
        "auto_top_up": False,
        "unknown_cost_action": BLOCK,
        "approval_reuse": False,
        "approvals_are_portable": False,
        "free_tier_requires_verified_zero_cost": True,
        "status": "ENFORCED_BY_NATIVE_GUARD_AT_CHECKED_ENTRYPOINTS",
    }


def evaluate(event: str, cost_class: str = "UNKNOWN", *,
             evidence: Mapping | None = None,
             approval: Mapping | None = None) -> dict:
    """Fail closed unless zero cost is evidenced or consent is action-scoped.

    Approval is accepted only as an explicit, fresh, non-portable argument from
    an authorized host. No approval is saved to a handoff or read from history.
    An approval cannot authorize an unknown monetary limit or automatic top-up.
    """
    event = event.upper() if isinstance(event, str) else ""
    cost_class = cost_class.upper() if isinstance(cost_class, str) else ""
    if event not in EVENTS or cost_class not in COST_CLASSES:
        raise ValueError("Unknown cost guard event or cost class")
    reference = evidence if isinstance(evidence, Mapping) else {}
    verified_free = (cost_class == "VERIFIED_FREE"
                     and reference.get("verified_zero_cost") is True
                     and isinstance(reference.get("source"), str)
                     and bool(reference.get("source").strip()))
    consent = approval if isinstance(approval, Mapping) else {}
    # Explicit approval must name this exact event, an action identifier, and
    # an exact numeric monetary cap; booleans are not numbers.
    limit = consent.get("max_eur")
    permitted = (consent.get("explicit") is True
                 and consent.get("event") == event
                 and isinstance(consent.get("action_id"), str)
                 and bool(consent["action_id"].strip())
                 and type(limit) in (int, float)
                 and 0 <= limit < float("inf")
                 and consent.get("allow_auto_top_up") is not True)
    # Unknown costs cannot be bounded reliably, even with a nominal approval.
    authorized = verified_free or (permitted and cost_class in {"PAID", "USES_PAID_CREDITS"})
    return {
        "policy_id": POLICY_ID,
        "schema_version": VERSION,
        "event": event,
        "cost_class": cost_class,
        "status": "VERIFIZIERT" if verified_free else ("APPROVAL_SCOPED" if authorized else BLOCK),
        "allowed": bool(authorized),
        "reason": ("Verifizierte kostenlose Ausführung."
                   if verified_free else
                   ("Explizite, auf diesen Vorgang begrenzte Freigabe."
                    if authorized else
                    "Kein nachgewiesener Nullkostenpfad oder gültige ausdrückliche Freigabe.")),
        "needs_explicit_approval": not verified_free,
        "evidence_source": reference.get("source") if verified_free else None,
        "approval_limit_eur": limit if authorized and not verified_free else None,
    }


def event_notice(event: str) -> dict:
    """Cost policy rehydration notice; does not execute external services."""
    return {
        "event": event,
        "policy": policy_snapshot(),
        "guard": evaluate(event),
        "next_step": "Kostenklasse und nachweisbare Nullkostenquelle vor externem Aufruf prüfen.",
    }
