"""R14 native host execution receipt for the exact existing R12 adapter.

A host supplies real authorized *read-only* GitHub callables to this module.
The module executes R12 itself, revalidates pinned local Git/module source,
records only sanitized call metadata and writes an append-only local receipt.
Neither an injected callback nor a receipt proves the ChatGPT plugin identity:
an independently attested plugin-host receipt remains a separate gate.
"""
from __future__ import annotations

import hashlib
import os
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path

from ..core import ROOT, WORK, DevhubError, git, read_json
from .codeforge_host_binding import verify_with_host

SCHEMA = "666dev-codeforge-host-receipt/v1"
MODULE = "src/devhub/intelligence/codeforge_host_binding.py"
SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _fail(reason: str) -> None:
    raise DevhubError("READBACK_PENDING: " + reason)


def execute_with_receipt(
    request: object, *, expected_source_commit: str, expected_module_blob: str,
    branch_fetch: Callable | None = None, file_fetch: Callable | None = None,
    receipt_root: Path | None = None,
) -> dict:
    """Run ORIGINAL R12 function, not an equivalent rewritten implementation.

    Only host-injected callable handles are used. No native or foreign writes,
    no arbitrary host dispatch and no automatic GitHub plugin discovery.
    """
    if not (isinstance(expected_source_commit, str)
            and SHA40.fullmatch(expected_source_commit)
            and isinstance(expected_module_blob, str)
            and SHA40.fullmatch(expected_module_blob)):
        _fail("Immutable Git commit and exact module Git blob SHA are mandatory.")
    if not callable(branch_fetch) or not callable(file_fetch):
        _fail("Authorized read-only GitHub host handles are unavailable.")
    try:
        observed_head = git(ROOT, "rev-parse", "--verify", "HEAD^{commit}")
        observed_module = git(ROOT, "hash-object", MODULE)
    except (DevhubError, OSError) as exc:
        _fail("Cannot read current Git commit and original module blob.")
    if observed_head != expected_source_commit or observed_module != expected_module_blob:
        _fail("Actual checkout/module differs from expected immutable Git proof.")

    if not isinstance(request, Mapping) or set(request) != {
        "peer", "branch", "path", "expected_head", "expected_blob"
    } or any(not isinstance(value, str) for value in request.values()):
        _fail("Host request must be an exact five-field string-only object.")
    argument_sha256 = hashlib.sha256(json.dumps(
        request, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")).hexdigest()
    receipt_id = hashlib.sha256(
        (expected_source_commit + ":" + expected_module_blob + ":" +
         argument_sha256).encode("ascii")
    ).hexdigest()[:32]
    folder = (receipt_root if receipt_root is not None
              else WORK / "codeforge-host-receipts").resolve()
    if receipt_root is None and not folder.is_relative_to(WORK.resolve()):
        _fail("Receipt path escapes ignored 666DEV workspace.")
    destination = folder / (receipt_id + ".json")
    lock_path = folder / (receipt_id + ".lock")
    folder.mkdir(parents=True, exist_ok=True)
    if (folder.is_symlink() or destination.is_symlink() or lock_path.is_symlink()
            or not destination.resolve().is_relative_to(folder)
            or not lock_path.resolve().is_relative_to(folder)):
        raise DevhubError("WRITE_BLOCKED: receipt workspace is symlinked or unsafe.")
    if destination.exists():
        raise DevhubError("CONFLICT_QUARANTINE: duplicate host receipt; no replay.")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DevhubError("CONFLICT_QUARANTINE: competing host execution is already locked.") from exc
    try:
        os.close(descriptor)
        if destination.exists():
            raise DevhubError("CONFLICT_QUARANTINE: receipt published while locking.")
        counters = {"branch": 0, "file": 0}

        def observed_branch(*, url: str):
            counters["branch"] += 1
            return branch_fetch(url=url)

        def observed_file(*, repository_full_name: str, path: str, ref: str):
            counters["file"] += 1
            return file_fetch(repository_full_name=repository_full_name,
                              path=path, ref=ref)

        # Execute the ORIGINAL R12 module, never a user-supplied replacement.
        try:
            result = verify_with_host(request, branch_fetch=observed_branch,
                                      file_fetch=observed_file)
        except Exception as exc:
            result = {"status": "READBACK_PENDING", "source_readback_verified": False,
                      "reason": "Provider invocation failed: " + type(exc).__name__}
        # Compare-and-swap revalidation after every external invocation.
        # Changed source cannot be turned into a verified or persisted receipt.
        if (git(ROOT, "rev-parse", "--verify", "HEAD^{commit}") != expected_source_commit
                or git(ROOT, "hash-object", MODULE) != expected_module_blob):
            raise DevhubError("CONFLICT_QUARANTINE: native source/module changed during host execution.")
        verified_source = (result.get("status") == "VERIFIZIERT"
                           and result.get("source_readback_verified") is True
                           and result.get("provider_binding_invoked") is True
                           and counters == {"branch": 2, "file": 1})
        status = ("PARTIAL" if verified_source else
                  "CONFLICT_QUARANTINE" if result.get("status") == "CONFLICT_QUARANTINE"
                  else "READBACK_PENDING")
        receipt = {
            "schema": SCHEMA, "authority": "666DEV",
            "source_commit": expected_source_commit,
            "original_module": MODULE, "original_module_blob": observed_module,
            "request_sha256": argument_sha256, "receipt_id": receipt_id,
            "provider_calls": counters,
            "original_adapter_executed": True,
            "source_readback_verified": verified_source,
            "adapter_status": result.get("status"), "peer": result.get("peer"),
            "peer_source": result.get("source") if verified_source else None,
            "status": status, "host_runtime_identity": "UNATTESTED",
            "chatgpt_plugin_host_verified": False,
            "github_connector_host_verified": False,
            "foreign_write_authorized": False, "peer_execution_verified": False,
            "current_updated": False,
            "reason": ("Original R12 adapter called with guarded handles; independent "
                       "plugin host identity/return receipt remains unverified."
                       if verified_source else "Adapter declined peer source verification."),
        }
        try:
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(receipt, stream, sort_keys=True, ensure_ascii=False)
                stream.write("\n")
        except FileExistsError as exc:
            raise DevhubError("CONFLICT_QUARANTINE: duplicate receipt; no overwrite.") from exc
        if read_json(destination) != receipt:
            _fail("Local host receipt readback mismatch.")
        return {**receipt, "receipt_path": str(destination)}
    finally:
        lock_path.unlink(missing_ok=True)
