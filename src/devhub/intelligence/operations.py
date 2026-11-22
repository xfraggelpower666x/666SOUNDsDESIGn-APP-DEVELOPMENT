"""Evidence-bound Operations Center for 666DEV.

This is a view model, not an executor, controller, persistence system or
replacement for native LiveCircle. Callers must obtain a fresh native snapshot.
"""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

from .cost_guard import event_notice

SCHEMA = "666dev-operations-center/v1"
FACET_SCHEMA = "666dev-facet-livecircle/v1"
FACETS = (
    ("overview", "Operations Center", "Native source and acceptance"),
    ("codeforge", "CodeForge", "Source analysis and controlled repair"),
    ("repomind", "Repo Mind", "Repository topology and impact"),
    ("continuity", "LiveCircle", "Working, Current and return anchors"),
    ("visual", "Visual Intelligence", "Views, charts and evidence-bound menus"),
    ("desktop", "Windows Control", "Desktop and host-acceptance checks"),
    ("coding-profi", "Coding Profi Intelligence", "Read-only adaptive coding intelligence with facet continuity"),
)
STATUSES = {"VERIFIZIERT", "ABGELEITET", "VORGESCHLAGEN", "OFFEN",
            "BLOCKIERT", "PARTIAL", "WRITE_BLOCKED", "READBACK_PENDING",
            "CONFLICT_QUARANTINE"}
HOLDS = {"BLOCKIERT", "WRITE_BLOCKED", "READBACK_PENDING", "CONFLICT_QUARANTINE"}

def _bound(native: Mapping[str, Any] | None) -> bool:
    return bool(isinstance(native, Mapping) and native.get("authority") == "666DEV"
                and isinstance(native.get("project_id"), str) and native["project_id"])

def _status(native: Mapping[str, Any] | None) -> str:
    if not native:
        return "OFFEN"
    value = native.get("status")
    return value if isinstance(value, str) and value in STATUSES else "READBACK_PENDING"

def _proof(native: Mapping[str, Any] | None) -> dict:
    return {key: native.get(key) if native else None
            for key in ("hub_commit", "source_commit", "profile_sha256")}

def facet_projection(facet_id: str, native: Mapping[str, Any] | None,
                     persisted: Mapping[str, Any] | None = None) -> dict:
    """Sub-LifeCircle display only; no second persistence or authority."""
    if facet_id not in {item[0] for item in FACETS}:
        raise ValueError("Unregistered 666DEV facet")
    bound = _bound(native)
    value = _status(native) if bound else "OFFEN"
    accepted = persisted if isinstance(persisted, Mapping) else None
    restored = accepted.get("checkpoint") if accepted and accepted.get("status") == "VERIFIZIERT" else None
    if not isinstance(restored, Mapping):
        restored = None
    return {
        "schema": FACET_SCHEMA, "owner": "666DEV", "facet_id": facet_id,
        "project_id": native["project_id"] if bound else None,
        "status": value, "source": _proof(native if bound else None),
        "working": native.get("working") if bound else None,
        "current": native.get("current") if bound else None,
        "return_anchor": native.get("return_anchor") if bound else None,
        "last_verified_step": restored.get("last_verified_step") if restored else None,
        "obligations": list(restored.get("obligations", [])) if restored else [],
        "evidence_ids": list(restored.get("evidence_ids", [])) if restored else [],
        "work_state": restored.get("state") if restored else None,
        "facet_return_anchor": restored.get("return_anchor") if restored else None,
        "checkpoint_digest": accepted.get("digest") if accepted else None,
        "step_evidence_status": "OFFEN",  # durable record integrity != observed task outcome
        "rehydration": ("READBACK_PENDING" if not bound or value in HOLDS else
                        accepted.get("status") if accepted else "NATIVE_SNAPSHOT_PROJECTION_ONLY"),
        "rehydration_reason": accepted.get("reason") if accepted else "No persisted facet read supplied.",
        "writable": False,
    }

def _next(native: Mapping[str, Any] | None) -> dict:
    if not _bound(native):
        return {"label": "Projekt auswählen", "action": None, "eligible": False,
                "reason": "Keine native Projektbindung.", "evidence": [],
                "countercheck": "Projekt-ID mit Registry und Profil prüfen."}
    project, status = native["project_id"], _status(native)
    if status in HOLDS:
        verb, reason = "LIVECIRCLE", "Native Quelle gesperrt oder nicht ausreichend gelesen."
    elif status == "PARTIAL" or native.get("working_tree_clean") is False:
        verb, reason = "IMPACT", "Quelländerungen beziehungsweise partielle Basis prüfen."
    elif any(isinstance(value, dict) and (value.get("failed", 0) or value.get("blocked", 0))
             for value in (native.get("acceptance") or {}).values()):
        verb, reason = "STATUS", "Fehlgeschlagene oder blockierte Prüfungen untersuchen."
    else:
        verb, reason = "LIVECIRCLE", "Arbeitsstand erneut gegen die native Quelle prüfen."
    return {"label": {"LIVECIRCLE": "LiveCircle prüfen", "IMPACT": "Änderungsfolgen prüfen",
                       "STATUS": "Prüfbelege untersuchen"}[verb],
            "action": ["666DEV", project, verb], "eligible": True,
            "kind": "read_only", "reason": reason,
            "evidence": ["native.status", "native.source_commit"],
            "countercheck": "Quellstand und Prüfergebnis direkt zurücklesen."}

def build_operations_center(native: Mapping[str, Any] | None = None,
                            *, registry: Mapping[str, str] | None = None,
                            facet_records: Mapping[str, dict] | None = None) -> dict:
    """Construct advisory view from a *caller-verified* native snapshot."""
    bound = _bound(native)
    value = _status(native) if bound else "OFFEN"
    verified = native if bound else None
    return {
        "schema": SCHEMA, "authority": "666DEV", "mode": "READ_ONLY_ADVISORY",
        "project_id": native["project_id"] if bound else None, "status": value,
        "source": _proof(verified),
        "projects": sorted(registry) if isinstance(registry, Mapping) else [],
        "facets": [facet_projection(item[0], verified, (facet_records or {}).get(item[0])) for item in FACETS],
        "navigation": [{"id": fid, "title": title, "description": detail}
                       for fid, title, detail in FACETS],
        "cost_consent": event_notice("REHYDRATE"),
        "visual_daemon": {
            "state": "HOLD" if value in HOLDS else "ADVISORY",
            "observed_status": value,
            "primary_action": _next(verified),
            "can_autowrite": False, "can_run_background": False,
        },
        "source_evidence_types": ["SOURCE", "LOCAL_TEST", "CI", "DELIVERY",
                                  "ADOPTION", "HOST"],
        "host_acceptance": "OFFEN", "plugin_acceptance": "OFFEN",
        "design_only": False,
    }
