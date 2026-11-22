"""666DEV-owned read-only consumer for the exact published CLIC R06 outbox handoff.

Never imports foreign runtime, runs embedded commands, writes state, mutates
another repository, or accepts history/backup as current. GitHub observations
must be gathered independently by the caller before review.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

SCHEMA = "CLIC_NATIVE_DEVELOPMENT_HANDOFF_V1"
HANDOFF_ID = "CLIC-TO-666DEV-R06-20261122-01"
SOURCE_REPO = "xfraggelpower666x/666CLICPRO"
SOURCE_BRANCH = "clic-migration-rev79-staging"
SOURCE_PATH = "666CLIC_NATIVE_RUNTIME/outbox/666DEV/" + HANDOFF_ID + ".json"
RECIPIENT_REPO = "xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT"
RECIPIENT_BRANCH = "666DEV"
REQUIRED_FINDINGS = ("DEV-01", "DEV-02", "DEV-03", "DEV-04")
SHA = re.compile(r"^[a-f0-9]{40}$")


def _sha(value: object) -> bool:
    return isinstance(value, str) and bool(SHA.fullmatch(value))


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def inspect(envelope: object, *, source_head: str | None = None,
            source_blob: str | None = None,
            recipient_current: str | None = None,
            recipient_head: str | None = None) -> dict:
    """Verify an envelope against caller-observed GitHub revisions; advisory only.

    Observed SHAs are not independently fetched by this pure function.
    A verified external caller must read current source HEAD + blob and the
    recipient's native Current before providing those observations.
    """
    details = {
        "handoff_id": HANDOFF_ID, "source_repo": SOURCE_REPO,
        "source_path": SOURCE_PATH, "source_blob": source_blob,
        "source_commit": source_head, "recipient_head": recipient_head,
        "recipient_current": recipient_current, "receipt_id": None,
        "native_decision": "READBACK_PENDING", "status": "READBACK_PENDING",
        "write_authorized": False, "host_accepted": False,
        "foreign_authority_accepted": False, "triggers_executed": False,
        "reason": "Independent source and recipient observations required.",
    }
    if not isinstance(envelope, Mapping):
        return details
    src = envelope.get("source")
    target = envelope.get("target_observed")
    findings = envelope.get("findings")
    if not isinstance(src, Mapping) or not isinstance(target, Mapping) or not isinstance(findings, list):
        return {**details, "status": "CONFLICT_QUARANTINE",
                "reason": "Malformed envelope sections."}
    expected = (
        envelope.get("schema") == SCHEMA
        and envelope.get("handoff_id") == HANDOFF_ID
        and envelope.get("source_system") == "666CLIC"
        and envelope.get("target") == "666DEV"
        and src.get("repository") == SOURCE_REPO
        and src.get("branch") == SOURCE_BRANCH
        and target.get("repository") == RECIPIENT_REPO
        and target.get("branch") == RECIPIENT_BRANCH
        and envelope.get("status") == "PREPARED"
        and envelope.get("automatic_foreign_activation") is False
        and envelope.get("foreign_mutation") is False
        and envelope.get("no_cross_system_merge") is True
        and envelope.get("native_adoption_verified") is False
        and envelope.get("host_acceptance") is False
        and envelope.get("delivery_receipt") is None
        and envelope.get("target_readback") is None
        and set(x.get("id") for x in findings if isinstance(x, Mapping)) == set(REQUIRED_FINDINGS)
        and len(findings) == len(REQUIRED_FINDINGS)
        and _sha(src.get("verified_base_head"))
        and _sha(target.get("head"))
    )
    if not expected:
        return {**details, "status": "CONFLICT_QUARANTINE",
                "reason": "Foreign authority, malformed identity, or contradictory handoff evidence."}
    if not all(_sha(x) for x in (source_head, source_blob, recipient_current, recipient_head)):
        return details
    if source_head == src["verified_base_head"]:
        # A source base is provenance, never the published handoff commit.
        return {**details, "status": "READBACK_PENDING",
                "reason": "Source base is not independently verified publication HEAD."}
    if recipient_current != target["head"]:
        return {**details, "status": "CONFLICT_QUARANTINE",
                "reason": "Recipient productive Current differs from source observation."}
    if not envelope.get("no_new_router") is True:
        return {**details, "status": "CONFLICT_QUARANTINE", "reason": "Unexpected routing authority."}
    receipt_id = "DEV-CLIC-R06-" + _digest({
        "handoff": HANDOFF_ID, "source_commit": source_head, "source_blob": source_blob,
        "recipient_current": recipient_current, "recipient_head": recipient_head,
    })[:20]
    return {
        **details, "receipt_id": receipt_id,
        "native_decision": "REVIEWED_READ_ONLY_NO_AUTHORITY_TRANSFER",
        "status": "PARTIAL",
        "reason": "Source IDs matched caller readback; independent integration, CI and host acceptance pending.",
        "source_evidence": "CALLER_OBSERVED_GITHUB_NOT_FETCHED_BY_CONSUMER",
        "adoption_verified": False,
        "findings": {item["id"]: item["status"] for item in findings},
    }
