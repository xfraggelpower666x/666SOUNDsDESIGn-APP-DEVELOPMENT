"""R13 live *GitHub Actions* host exercise of the exact R12 Python adapter.

Real public GitHub REST GET callbacks are injected into the original R12 module.
This is not ChatGPT connector/plugin-host acceptance. No secrets, writes or paid API.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

from devhub.intelligence.codeforge_host_binding import verify_with_host

PEER_REPO = "xfraggelpower666x/666CLICPRO"
BRANCH = "clic-migration-rev79-staging"
PATH = "666CLIC_NATIVE_RUNTIME/outbox/666DEV/CLIC-TO-666DEV-R06-20261122-01.json"
EXPECTED_HEAD = "642a775118b877c0f7621f71c395c1fe1f80791c"
EXPECTED_BLOB = "f21d5734292ac262c76d136e9c3af642397f2066"
API = "https://api.github.com/repos/" + PEER_REPO
MAX_BYTES = 128 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_json(url: str) -> dict:
    if not url.startswith(API + "/"):
        raise ValueError("GitHub host URL outside pinned peer")
    req = Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "666DEV-R13-Actions-Live-Host-Acceptance",
    }, method="GET")
    with build_opener(_NoRedirect).open(req, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError("Non-200 GitHub response")
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Oversized GitHub response")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return parsed


def run_live() -> dict:
    counters = {"branch": 0, "file": 0}
    def branch_fetch(*, url: str) -> dict:
        if url != API + "/branches/" + quote(BRANCH, safe=""):
            raise ValueError("Unapproved branch lookup")
        counters["branch"] += 1
        payload = _http_json(url)
        return {"result": {"content": json.dumps({
            "name": payload.get("name"), "commit": {
                "sha": payload.get("commit", {}).get("sha")}
        })}}

    def file_fetch(*, repository_full_name: str, path: str, ref: str) -> dict:
        if (repository_full_name != PEER_REPO or path != PATH or
                ref != EXPECTED_HEAD):
            raise ValueError("Unapproved file lookup")
        counters["file"] += 1
        payload = _http_json(API + "/contents/" + quote(path, safe="/") +
                             "?ref=" + ref)
        if (payload.get("type") != "file" or
                payload.get("encoding") != "base64" or
                payload.get("sha") != EXPECTED_BLOB):
            raise ValueError("Unexpected GitHub file metadata")
        raw = base64.b64decode(payload["content"], validate=True)
        if len(raw) != payload.get("size"):
            raise ValueError("GitHub file size mismatch")
        # Exact R12 transport expects UTF-8 text, not binary.
        return {"result": {"content": raw.decode("utf-8"), "sha": payload["sha"]}}

    request = {"peer": "666CLIC", "branch": BRANCH, "path": PATH,
               "expected_head": EXPECTED_HEAD, "expected_blob": EXPECTED_BLOB}
    result = verify_with_host(
        request, branch_fetch=branch_fetch, file_fetch=file_fetch)
    accepted = (result["status"] == "VERIFIZIERT"
                and result["source_readback_verified"] is True
                and result["provider_binding_invoked"] is True
                and result["source"]["source_commit"] == EXPECTED_HEAD
                and result["source"]["git_blob_sha"] == EXPECTED_BLOB
                and counters == {"branch": 2, "file": 1}
                and result["provider_host_verified"] is False
                and result["plugin_host_verified"] is False
                and result["foreign_write_authorized"] is False
                and result["current_updated"] is False)
    return {
        "schema": "666dev-r13-live-actions-receipt/v1",
        "authority": "666DEV",
        "execution_host": "GITHUB_ACTIONS_PYTHON",
        "module": "devhub.intelligence.codeforge_host_binding.verify_with_host",
        "transport": "LIVE_GITHUB_PUBLIC_REST_GET_INJECTED",
        "source_verified": bool(accepted),
        "host_process_executed": True,
        "github_connector_host_verified": False,
        "chatgpt_plugin_host_verified": False,
        "peer_plugin_execution_verified": False,
        "native_current_updated": False,
        "foreign_write": False,
        "requests": counters,
        "peer_repo": PEER_REPO,
        "peer_branch": BRANCH,
        "peer_head": EXPECTED_HEAD,
        "peer_blob": EXPECTED_BLOB,
        "adapter_status": result["status"],
        "status": "VERIFIZIERT" if accepted else "READBACK_PENDING",
    }


def main() -> int:
    try:
        receipt = run_live()
    except (HTTPError, URLError, ValueError, RuntimeError, KeyError,
            UnicodeError, TypeError) as exc:
        receipt = {
            "schema": "666dev-r13-live-actions-receipt/v1",
            "execution_host": "GITHUB_ACTIONS_PYTHON",
            "status": "READBACK_PENDING",
            "error_type": type(exc).__name__,
            "chatgpt_plugin_host_verified": False,
        }
    # Print sanitized metadata and digests only, no peer content, no tokens.
    print("R13_LIVE_RECEIPT=" + json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "VERIFIZIERT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
