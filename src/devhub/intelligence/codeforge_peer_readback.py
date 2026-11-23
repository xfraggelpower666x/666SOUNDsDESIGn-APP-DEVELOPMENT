"""R11: revision-bound public GitHub peer readback for native 666DEV CodeForge.

Public, read-only GitHub metadata/file transport. No tokens, private data,
foreign routing, plugin invocation, cross-repo writes, or Current promotion.
Only independently registered peers and exact user-supplied SHAs are eligible.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .cost_guard import evaluate

SCHEMA = "666dev-peer-github-readback/v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
BRANCH = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,199}$")
PATH = re.compile(r"^[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)*$")
MAX_BODY = 128 * 1024
MAX_FILE = 48 * 1024
# These identities were observed via GitHub repo metadata. A repository ID is
# only an allowed *source* for data, never native Current or write authority.
PEER_REPOSITORIES = {
    "666CLIC": "xfraggelpower666x/666CLICPRO",
    "666MAIN_BRAIN": "xfraggelpower666x/666MAIN_BRAIN_MYCEL_SYSTEM",
}
SOURCE_PREFIXES = {
    "666CLIC": ("666CLIC_NATIVE_RUNTIME/outbox/666DEV/",),
    "666MAIN_BRAIN": ("666MAIN_BRAIN_NATIVE_RUNTIME/", "PROJECTS/", "handoffs/"),
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get_json(url: str) -> dict:
    """Single no-auth API GET, bounded bytes, no redirect, no retry."""
    if not url.startswith("https://api.github.com/repos/xfraggelpower666x/"):
        raise ValueError("Untrusted GitHub endpoint.")
    req = Request(url, headers={"Accept": "application/vnd.github+json",
                                 "User-Agent": "666DEV-native-peer-readback",
                                 "X-GitHub-Api-Version": "2022-11-28"},
                  method="GET")
    with build_opener(_NoRedirect).open(req, timeout=12) as response:
        if response.status != 200:
            raise ValueError("GitHub readback returned a non-success status.")
        data = response.read(MAX_BODY + 1)
        if len(data) > MAX_BODY:
            raise ValueError("GitHub API response exceeds safe bound.")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("GitHub API response must be an object.")
    return parsed


def _failed(status: str, reason: str, *, peer: str | None = None) -> dict:
    return {
        "schema": SCHEMA, "authority": "666DEV", "peer": peer,
        "status": status, "source_readback_verified": False,
        "peer_native_current_verified": False, "host_plugin_verified": False,
        "peer_execution_verified": False, "write_authorized": False,
        "foreign_authority_adopted": False, "current_updated": False,
        "reason": reason,
    }


def inspect(request: object, *, fetch=None) -> dict:
    """Read verified public peer file at immutable commit, then recheck branch.

    The request is untrusted input. The registered repo mapping is *code-owned*.
    SOURCE readback does not imply host plugin execution or native Peer Current.
    """
    if not isinstance(request, Mapping) or set(request) != {
        "peer", "branch", "path", "expected_head", "expected_blob"
    }:
        return _failed("CONFLICT_QUARANTINE", "Invalid peer readback request schema.")
    peer, branch, path = request["peer"], request["branch"], request["path"]
    head, blob = request["expected_head"], request["expected_blob"]
    if not isinstance(peer, str) or peer not in PEER_REPOSITORIES:
        return _failed("CONFLICT_QUARANTINE", "Unregistered foreign peer.")
    if (not isinstance(branch, str) or not BRANCH.fullmatch(branch)
        or ".." in branch or "//" in branch or branch.endswith(("/", ".", ".lock"))
        or not isinstance(path, str) or not PATH.fullmatch(path)
        or any(x in ("", ".", "..") for x in path.split("/"))
        or not path.endswith((".json", ".md"))
        or not any(path.startswith(root) for root in SOURCE_PREFIXES[peer])
        or not isinstance(head, str) or not SHA40.fullmatch(head)
        or not isinstance(blob, str) or not SHA40.fullmatch(blob)):
        return _failed("CONFLICT_QUARANTINE", "Invalid branch, allowed path or pinned SHA.", peer=peer)
    cost = evaluate("API_CALL", "VERIFIED_FREE", evidence={
        "verified_zero_cost": True,
        "source": "public GitHub REST API unauthenticated GET; no paid token or credits",
    })
    if not cost["allowed"]:
        return _failed("WRITE_BLOCKED", "Zero-cost GitHub read not authorized.", peer=peer)
    repo = PEER_REPOSITORIES[peer]
    base = "https://api.github.com/repos/" + repo
    branch_url = base + "/branches/" + quote(branch, safe="")
    file_url = base + "/contents/" + quote(path, safe="/") + "?ref=" + head
    getter = _get_json if fetch is None else fetch
    try:
        first = getter(branch_url)
        if first.get("name") != branch or not isinstance(first.get("commit"), Mapping):
            return _failed("CONFLICT_QUARANTINE", "Returned branch identity differs.", peer=peer)
        if first["commit"].get("sha") != head:
            return _failed("READBACK_PENDING", "Peer branch HEAD differs from pinned request.", peer=peer)
        found = getter(file_url)
        if found.get("type") != "file" or found.get("path") != path or found.get("sha") != blob:
            return _failed("CONFLICT_QUARANTINE", "File identity or Git blob SHA differs.", peer=peer)
        if (found.get("encoding") != "base64" or type(found.get("size")) is not int
            or not 0 <= found["size"] <= MAX_FILE or not isinstance(found.get("content"), str)):
            return _failed("CONFLICT_QUARANTINE", "Untrusted blob format or size.", peer=peer)
        raw = base64.b64decode(found["content"], validate=True)
        if len(raw) != found["size"] or len(raw) > MAX_FILE:
            return _failed("CONFLICT_QUARANTINE", "File size does not match metadata.", peer=peer)
        measured_blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                                     b"\\0" + raw).hexdigest()
        if measured_blob != blob:
            return _failed("CONFLICT_QUARANTINE", "Bytes disagree with Git blob SHA.", peer=peer)
        second = getter(branch_url)
        if (second.get("name") != branch or not isinstance(second.get("commit"), Mapping)
                or second["commit"].get("sha") != head):
            return _failed("READBACK_PENDING", "Branch moved during GitHub peer readback.", peer=peer)
    except (ValueError, TypeError, KeyError, UnicodeError, HTTPError, URLError,
            OSError, json.JSONDecodeError) as exc:
        return _failed("READBACK_PENDING",
                       "GitHub source readback failed: " + type(exc).__name__, peer=peer)
    return {
        "schema": SCHEMA, "authority": "666DEV", "peer": peer,
        "repository": repo, "branch": branch, "path": path,
        "source_commit": head, "git_blob_sha": measured_blob,
        "bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_size": len(raw),
        "status": "VERIFIZIERT", "source_readback_verified": True,
        "peer_native_current_verified": False,
        "host_plugin_verified": False, "peer_execution_verified": False,
        "write_authorized": False, "foreign_authority_adopted": False,
        "current_updated": False,
        "reason": "Exact public GitHub branch/commit/blob/bytes verified twice; peer Current, delivery, adoption and host remain separate.",
    }
