"""666DEV-native CodeForge peer cooperation: read-only composition, never dispatch.

LYVRA Coding Profi leads *method selection and review order* when requested.
Actual patch/build/write authority always belongs to each verified native owner.
Partner data are external proposals, not current native state or host handles.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

SCHEMA = "666dev-codeforge-team/v1"
SHA = re.compile(r"^[0-9a-f]{40}$")
OWNER = "666DEV"
LEAD = "LYVRA_CODING_PROFI"
PEERS = (
    ("LYVRA_CODING_PROFI", "METHOD_LEAD"),
    ("666DEV", "NATIVE_IMPLEMENTER"),
    ("LYVRA_SUPERCODEFORGE", "PEER_REVIEW"),
    ("666CLIC", "SEMANTIC_INTEGRATION_REVIEW"),
    ("666MAIN_BRAIN", "SHARED_CAPABILITY_ADVISOR"),
    ("CODER", "WEB_APP_SPECIALIST"),
)
PEER_IDS = frozenset(identity for identity, _ in PEERS)
SAFE_STATES = frozenset({"VERIFIZIERT", "ABGELEITET", "PARTIAL", "READBACK_PENDING"})


def catalog() -> dict:
    """Capability catalog, not plugin-host or live repository evidence."""
    return {
        "schema": SCHEMA,
        "owner": OWNER,
        "method_lead": LEAD,
        "method_lead_authority": "ADVISORY_ONLY",
        "native_execution_authority": "PER_OWNER_CURRENT",
        "participants": [{"id": identity, "role": role} for identity, role in PEERS],
        "seven_facets_preserved": True,
        "cost_contract": "ZERO_ADDITIONAL_EUR_DEFAULT",
        "dispatch_enabled": False,
        "external_writes_enabled": False,
        "provider_host_verified": False,
        "status": "READBACK_PENDING",
        "reason": "Methods are available, but peer current and provider host handles are unverified.",
    }


def plan(request: object, *, native: Mapping | None = None) -> dict:
    """Plan isolated workstreams from peer *proposals*, with no external calls."""
    result = {
        **catalog(),
        "plan_status": "READBACK_PENDING",
        "project_id": None,
        "waves": [],
        "blocked": [],
        "write_authorized": False,
        "executed": False,
        "peer_adoption_verified": False,
    }
    if not isinstance(request, Mapping) or set(request) != {"project_id", "workstreams"}:
        return {**result, "plan_status": "CONFLICT_QUARANTINE",
                "reason": "Request schema mismatch; expected only project_id and workstreams."}
    project = request["project_id"]
    entries = request["workstreams"]
    if (not isinstance(project, str) or not project or len(project) > 120
            or not isinstance(entries, list) or not 1 <= len(entries) <= 24):
        return {**result, "plan_status": "CONFLICT_QUARANTINE", "reason": "Invalid project/streams."}
    result["project_id"] = project
    if not isinstance(native, Mapping) or (native.get("authority") != OWNER
        or native.get("project_id") != project
        or not isinstance(native.get("source_commit"), str)
        or not SHA.fullmatch(native["source_commit"])
        or not isinstance(native.get("hub_commit"), str)
        or not SHA.fullmatch(native["hub_commit"])
        or not isinstance(native.get("profile_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", native["profile_sha256"])
        or native.get("status") not in ("VERIFIZIERT", "ABGELEITET", "PARTIAL")):
        return {**result, "reason": "Verified 666DEV project LiveCircle required."}
    revision = native["source_commit"]
    streams, identifiers = [], set()
    for index, item in enumerate(entries):
        if not isinstance(item, Mapping) or set(item) != {
            "id", "peer", "source_commit", "scope", "depends_on", "capability", "evidence_status"
        }:
            return {**result, "plan_status": "CONFLICT_QUARANTINE",
                    "reason": f"Malformed workstream at index {index}."}
        sid, peer = item["id"], item["peer"]
        paths, parents = item["scope"], item["depends_on"]
        if (not isinstance(sid, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", sid)
            or sid in identifiers or not isinstance(peer, str) or peer not in PEER_IDS
            or not isinstance(item["capability"], str) or not item["capability"].strip()
            or len(item["capability"]) > 128
            or not isinstance(item["source_commit"], str)
            or not SHA.fullmatch(item["source_commit"])
            or not isinstance(item["evidence_status"], str) or item["evidence_status"] not in SAFE_STATES
            or not isinstance(paths, list) or not paths or len(paths) > 40
            or not isinstance(parents, list) or len(parents) > 24
            or any(not isinstance(p, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", p
            ) or p in (".", "..") or "/../" in f"/{p}/" for p in paths)
            or any(not isinstance(d, str) for d in parents)
            or len(set(paths)) != len(paths) or len(set(parents)) != len(parents)):
            return {**result, "plan_status": "CONFLICT_QUARANTINE",
                    "reason": f"Untrusted workstream identity, paths or revision: {index}."}
        if peer == OWNER and item["source_commit"] != revision:
            return {**result, "plan_status": "CONFLICT_QUARANTINE",
                    "reason": "666DEV workstream source commit does not match native project revision."}
        identifiers.add(sid)
        streams.append({"id": sid, "peer": peer, "scope": paths,
                        "depends_on": parents, "source_commit": item["source_commit"],
                        "capability": item["capability"],
                        "evidence_status": item["evidence_status"]})
    if any(dep not in identifiers or dep == item["id"]
           for item in streams for dep in item["depends_on"]):
        return {**result, "plan_status": "CONFLICT_QUARANTINE",
                "reason": "Unknown or self dependency."}

    remaining = {item["id"]: item for item in streams}
    done = set()
    waves = []
    while remaining:
        candidates = [i for i in streams if i["id"] in remaining
                      and set(i["depends_on"]) <= done]
        if not candidates:
            return {**result, "plan_status": "CONFLICT_QUARANTINE",
                    "reason": "Dependency cycle prevents parallel planning."}
        wave, touched = [], set()
        for item in candidates:
            # A directory and a descendant overlap even without equal strings.
            overlapping = any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
                              for a in item["scope"] for b in touched)
            if overlapping:
                continue
            touched.update(item["scope"])
            wave.append(item)
        if not wave:
            return {**result, "plan_status": "CONFLICT_QUARANTINE",
                    "reason": "No nonconflicting wave available."}
        waves.append([{"id": i["id"], "peer": i["peer"], "scope": i["scope"],
                       "disposition": ("NATIVE_REVIEW_REQUIRED" if i["peer"] == OWNER
                                      else "PEER_PROPOSAL_ONLY"),
                       "source_commit": i["source_commit"]} for i in wave])
        for item in wave:
            del remaining[item["id"]]
            done.add(item["id"])
    return {**result, "plan_status": "PLAN_READY_NOT_DISPATCHED", "waves": waves,
            "source_revision": revision,
            "blocked": [i["id"] for i in streams if i["peer"] != OWNER
                        or i["evidence_status"] != "VERIFIZIERT"],
            "reason": "Workstreams ordered, not executed; verify each owner Current, permissions, cost and host before any action."}
