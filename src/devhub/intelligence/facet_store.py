"""Project-scoped persistent facet checkpoints; subordinate to native LiveCircle.

Never promotes a facet checkpoint to native Working/Current. All disk writes
require a checked 666DEV native snapshot and an explicit expected revision.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .. import core

SCHEMA = "666dev-facet-checkpoint/v1"
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}", re.ASCII)
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,62}", re.ASCII)
FACET_IDS = frozenset(("overview", "codeforge", "repomind", "continuity", "visual", "desktop"))
ALLOWED_STATES = frozenset(("READY", "ACTIVE", "WAITING", "PAUSED", "COMPLETED"))
BLOCKS = frozenset(("READBACK_PENDING", "CONFLICT_QUARANTINE", "WRITE_BLOCKED", "BLOCKIERT"))
MAX_BYTES = 16384


def _location(project_id: str, facet_id: str) -> Path:
    """Store local facet data outside tracked project/Current files."""
    if not ID.fullmatch(project_id) or project_id not in core.project_entries():
        raise core.DevhubError("Unknown project for facet checkpoint.")
    if facet_id not in FACET_IDS:
        raise core.DevhubError("Unknown facet ID.")
    root = (core.WORK / "facets").resolve()
    path = root / project_id / (facet_id + ".json")
    if path.exists() and path.is_symlink():
        raise core.DevhubError("Facet checkpoint symlink forbidden.")
    if path.parent.exists() and path.parent.is_symlink():
        raise core.DevhubError("Facet directory symlink forbidden.")
    if not path.resolve().is_relative_to(root):
        raise core.DevhubError("Facet checkpoint path escaped work root.")
    return path


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(payload: dict) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _native_proof(native: dict, project_id: str) -> dict:
    if not isinstance(native, dict) or native.get("authority") != "666DEV" or native.get("project_id") != project_id:
        raise core.DevhubError("Native 666DEV project authority missing.")
    if native.get("status") in BLOCKS or native.get("working_tree_clean") is not True:
        raise core.DevhubError("Native project is not safe for facet checkpoint writes.")
    source = native.get("source_commit")
    hub = native.get("hub_commit")
    fingerprint = native.get("profile_sha256")
    if not isinstance(source, str) or not SHA.fullmatch(source):
        raise core.DevhubError("Missing immutable source revision.")
    if not isinstance(hub, str) or not SHA.fullmatch(hub):
        raise core.DevhubError("Missing immutable hub revision.")
    if not isinstance(fingerprint, str) or not re.fullmatch("[0-9a-f]{64}", fingerprint):
        raise core.DevhubError("Missing profile fingerprint.")
    return {"hub_commit": hub, "source_commit": source, "profile_sha256": fingerprint,
            "working": native.get("working"), "current": native.get("current")}


def read_checkpoint(project_id: str, facet_id: str, native: dict) -> dict:
    """Read only. Compare saved identity/revision/parent pointers with native."""
    path = _location(project_id, facet_id)
    if not path.exists():
        return {"status": "OFFEN", "checkpoint": None, "digest": None,
                "reason": "No facet checkpoint exists."}
    try:
        if path.stat().st_size > MAX_BYTES or not path.is_file():
            raise ValueError("Checkpoint file invalid or too large.")
        record = core.read_json(path)
        if not isinstance(record, dict) or record.get("schema") != SCHEMA:
            raise ValueError("Checkpoint schema mismatch.")
        saved_digest = record.get("digest")
        body = {k: v for k, v in record.items() if k != "digest"}
        if not isinstance(saved_digest, str) or not re.fullmatch("[0-9a-f]{64}", saved_digest) or _digest(body) != saved_digest:
            raise ValueError("Checkpoint digest mismatch.")
        if record.get("project_id") != project_id or record.get("facet_id") != facet_id or record.get("authority") != "666DEV":
            raise ValueError("Checkpoint identity mismatch.")
        if not isinstance(record.get("state"), str) or record["state"] not in ALLOWED_STATES:
            raise ValueError("Facet state invalid.")
        if not isinstance(record.get("obligations"), list) or not isinstance(record.get("evidence_ids"), list):
            raise ValueError("Facet evidence list invalid.")
    except (OSError, ValueError, core.DevhubError):
        return {"status": "CONFLICT_QUARANTINE", "checkpoint": None, "digest": None,
                "reason": "Facet checkpoint corrupt, untrusted or inconsistent."}
    try:
        proof = _native_proof(native, project_id)
    except core.DevhubError:
        return {"status": "READBACK_PENDING", "checkpoint": None, "digest": saved_digest,
                "reason": "Fresh native project proof unavailable."}
    if record.get("source") != proof:
        return {"status": "PARTIAL", "checkpoint": None, "digest": saved_digest,
                "reason": "Facet checkpoint does not match current native revision or pointer."}
    return {"status": "VERIFIZIERT", "checkpoint": record, "digest": saved_digest,
            "reason": "Facet checkpoint matches current native project evidence."}


def save_checkpoint(project_id: str, facet_id: str, native: dict, *,
                    state: str, last_verified_step: str | None,
                    obligations: list[str], evidence_ids: list[str],
                    return_anchor: str | None,
                    expected_digest: str | None = None) -> dict:
    """Explicit CAS write. Must be called by an authorized native host only.

    expected_digest=None means a new checkpoint, not an unchecked overwrite.
    Existing records are immutable until their matching digest is supplied.
    """
    path = _location(project_id, facet_id)
    proof = _native_proof(native, project_id)
    if state not in ALLOWED_STATES:
        raise core.DevhubError("Invalid facet lifecycle state.")
    if not all(isinstance(x, str) and 0 < len(x) <= 256 for x in obligations + evidence_ids):
        raise core.DevhubError("Invalid obligations/evidence IDs.")
    if len(obligations) > 24 or len(evidence_ids) > 48:
        raise core.DevhubError("Facet evidence list too long.")
    if last_verified_step is not None and (not isinstance(last_verified_step, str) or len(last_verified_step) > 256):
        raise core.DevhubError("Invalid verified step.")
    if return_anchor is not None and (not isinstance(return_anchor, str) or len(return_anchor) > 256):
        raise core.DevhubError("Invalid return anchor.")
    if expected_digest is not None and (not isinstance(expected_digest, str) or not re.fullmatch("[0-9a-f]{64}", expected_digest)):
        raise core.DevhubError("Invalid expected checkpoint digest.")
    body = {"schema": SCHEMA, "authority": "666DEV", "project_id": project_id,
            "facet_id": facet_id, "source": proof, "state": state,
            "last_verified_step": last_verified_step, "obligations": obligations,
            "evidence_ids": evidence_ids, "return_anchor": return_anchor}
    if len(_canonical(body)) > MAX_BYTES - 120:
        raise core.DevhubError("Facet checkpoint exceeds storage limit.")
    root = (core.WORK / "facets").resolve()
    root.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise core.DevhubError("Facet symlink forbidden.")
    # Atomic exclusive lock protects the compare-and-swap from concurrent hosts.
    lock = path.with_suffix(".lock")
    fd = None
    acquired = False
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        acquired = True
        os.close(fd)
        fd = None
        existing = read_checkpoint(project_id, facet_id, native)
        if existing["status"] == "OFFEN":
            if expected_digest is not None:
                raise core.DevhubError("Checkpoint CAS mismatch: expected existing record.")
        elif existing["status"] == "VERIFIZIERT":
            if existing["digest"] != expected_digest:
                raise core.DevhubError("Checkpoint CAS mismatch: concurrent change.")
        else:
            raise core.DevhubError("Checkpoint requires recovery/revalidation before write.")
        # Re-check caller source before any mutation.
        from ..livecircle import snapshot
        fresh = snapshot(project_id)
        if _native_proof(fresh, project_id) != proof:
            raise core.DevhubError("Native project changed before facet checkpoint write.")
        record = {**body, "digest": _digest(body)}
        core.atomic_json(path, record)
        check = read_checkpoint(project_id, facet_id, fresh)
        if check["status"] != "VERIFIZIERT" or check["digest"] != record["digest"]:
            raise core.DevhubError("Facet checkpoint readback failed.")
        return check
    except FileExistsError as exc:
        raise core.DevhubError("Facet checkpoint is locked by another operation.") from exc
    finally:
        if fd is not None:
            os.close(fd)
        # Never remove a lock owned by another invocation.
        if acquired:
            lock.unlink(missing_ok=True)
