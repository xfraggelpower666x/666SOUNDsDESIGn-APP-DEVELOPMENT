"""R12 capability-bound GitHub host bridge for the existing R11 peer readback.

This is host handle injection, not plugin discovery or autonomous execution.
Only exact authorized read-only handles may be supplied by the live host.
"""
from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable, Mapping

from .codeforge_peer_readback import inspect, PEER_REPOSITORIES, SCHEMA as SOURCE_SCHEMA

SCHEMA = "666dev-peer-host-binding/v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
PROVIDER = "mcp__GitHub__fetch_file"
BRANCH_PROVIDER = "mcp__GitHub__fetch"
MAX_FILE = 48 * 1024


def _blocked(status: str, reason: str) -> dict:
    return {
        "schema": SCHEMA, "authority": "666DEV", "status": status,
        "source_readback_verified": False, "provider_binding_invoked": False,
        "provider_host_verified": False, "plugin_host_verified": False,
        "peer_execution_verified": False, "foreign_write_authorized": False,
        "current_updated": False, "reason": reason,
    }


def _unwrap(value: object) -> Mapping:
    """Accept host's result envelope, not caller-supplied provider claims."""
    if not isinstance(value, Mapping):
        raise ValueError("Provider response is not a mapping")
    result = value.get("result", value)
    if not isinstance(result, Mapping):
        raise ValueError("Provider result missing")
    if isinstance(result.get("content"), str) and "sha" not in result:
        parsed = json.loads(result["content"])
        if not isinstance(parsed, Mapping):
            raise ValueError("GitHub API content must be an object")
        return parsed
    return result


def verify_with_host(request: object, *, branch_fetch: Callable | None = None,
                     file_fetch: Callable | None = None) -> dict:
    """Invoke only the passed read-only host handles; never look them up.

    No general tool dispatcher, arbitrary URL or write handles enter this
    interface. Host binding identity requires separate live-host evidence.
    """
    if branch_fetch is None or file_fetch is None:
        return _blocked("READBACK_PENDING", "Both authorized GitHub read handles are required.")
    if not callable(branch_fetch) or not callable(file_fetch):
        return _blocked("WRITE_BLOCKED", "Provider handles must be callable.")
    if not isinstance(request, Mapping) or set(request) != {
        "peer", "branch", "path", "expected_head", "expected_blob"
    }:
        return _blocked("CONFLICT_QUARANTINE", "Malformed peer source request.")
    peer = request.get("peer")
    if not isinstance(peer, str) or peer not in PEER_REPOSITORIES:
        return _blocked("CONFLICT_QUARANTINE", "Peer repository not registered.")
    repo = PEER_REPOSITORIES[peer]
    # Run the complete R11 scope/path/SHA validation first, without network.
    # R11 validates before calling its transport: invoke with a sentinel that
    # raises at first valid fetch, then explicitly accept only that outcome.
    class _PreflightReached(Exception):
        pass

    def sentinel(_):
        raise _PreflightReached

    try:
        first = inspect(request, fetch=sentinel)
    except _PreflightReached:
        first = None
    if first is not None:
        return _blocked(first.get("status", "CONFLICT_QUARANTINE"),
                        first.get("reason", "R11 preflight rejected peer input."))
    head, branch, path = request["expected_head"], request["branch"], request["path"]
    if not SHA40.fullmatch(head):
        return _blocked("CONFLICT_QUARANTINE", "Invalid pinned source SHA.")

    calls = [0, 0]
    def fetch(url: str) -> dict:
        if "/branches/" in url:
            # R11 builds this precise branch URL using the validated request.
            calls[0] += 1
            if calls[0] > 2:
                raise ValueError("Excess branch fetch")
            payload = _unwrap(branch_fetch(url=url))
            revision = payload.get("commit")
            if not isinstance(revision, Mapping):
                raise ValueError("Missing branch commit")
            return {"name": payload.get("name"), "commit": {"sha": revision.get("sha")}}
        if "/contents/" in url:
            calls[1] += 1
            if calls[1] > 1:
                raise ValueError("Excess file fetch")
            # No path or repository from the URL are forwarded. They come only
            # from an already validated registered request.
            payload = _unwrap(file_fetch(repository_full_name=repo, path=path, ref=head))
            raw = payload.get("content")
            if not isinstance(raw, str):
                raise ValueError("Host file body must be plain UTF-8 text")
            encoded = raw.encode("utf-8")
            if len(encoded) > MAX_FILE:
                raise ValueError("Host file exceeds bounded GitHub peer scope")
            return {"type": "file", "path": path, "sha": payload.get("sha"),
                    "size": len(encoded), "encoding": "base64",
                    "content": base64.b64encode(encoded).decode("ascii")}
        raise ValueError("Unapproved readback request")

    inspected = inspect(request, fetch=fetch)
    return {
        "schema": SCHEMA, "authority": "666DEV", "peer": peer,
        "status": inspected["status"],
        "source_readback_verified": inspected["source_readback_verified"],
        "source": {key: inspected.get(key) for key in (
            "repository", "branch", "path", "source_commit", "git_blob_sha",
            "bytes_sha256", "byte_size") if key in inspected},
        "provider_binding_invoked": calls == [2, 1],
        # A test-injected callable can behave like a host. Never promote it to
        # independent host or plugin acceptance without runtime attestation.
        "provider_host_verified": False, "plugin_host_verified": False,
        "peer_execution_verified": False,
        "foreign_write_authorized": False, "current_updated": False,
        "provider_contract": [BRANCH_PROVIDER, PROVIDER],
        "reason": ("Source was verified through injected read-only bindings; host attestation remains separate."
                   if inspected["source_readback_verified"] else inspected["reason"]),
    }
