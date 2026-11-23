"""R10 native executable CodeForge: isolated patch, guarded local build, verified receipt.

Not a generic shell runner and never a foreign or automatic GitHub writer.
A direct 666DEV CLI action and immutable candidate SHA-256 are required.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from collections.abc import Mapping

from ..core import (DevhubError, ROOT, WORK, allowed_path, apply_candidate,
                    clean_source, git, rehydrate, run_acceptance, unresolved_conflicts,
                    atomic_json, read_json)
from .codeforge_cooperation import plan

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = "666dev-codeforge-execution/v1"


def _fail(message: str) -> None:
    raise DevhubError("WRITE_BLOCKED: " + message)


def _safe_candidate_path(project_dir: Path, relative: str) -> Path:
    from ..core import state_file
    if (not isinstance(relative, str) or not relative
            or "\\" in relative or ":" in relative
            or relative.startswith("/") or ".." in Path(relative).parts):
        _fail("candidate must use a project-relative safe path.")
    folder = state_file(project_dir, "patch-candidates")
    path = (folder / relative).resolve()
    if (not path.is_relative_to(folder) or not path.is_file() or path.is_symlink()
            or path.stat().st_size > 262144):
        _fail("candidate missing, symlinked, oversized or outside patch-candidates.")
    return path


def execute_native(
    proposal: object, *, workstream_id: str, candidate_relative: str,
    expected_candidate_sha256: str, native: Mapping | None,
) -> dict:
    """Real local change in an isolated worktree, not a project release.

    The caller must come from the explicit CLI EXECUTE command. This function
    cannot be used to grant authority to another peer or publish GitHub data.
    """
    if not isinstance(expected_candidate_sha256, str) or not HEX64.fullmatch(expected_candidate_sha256):
        _fail("exact candidate SHA-256 required.")
    reviewed = plan(proposal, native=native)
    if reviewed.get("plan_status") != "PLAN_READY_NOT_DISPATCHED":
        _fail("fresh native project plan is not ready.")
    if not reviewed["waves"] or not isinstance(workstream_id, str):
        _fail("no eligible workstream.")
    selected_wave = next((item for item in reviewed["waves"][0]
                          if item["id"] == workstream_id), None)
    if selected_wave is None or selected_wave["peer"] != "666DEV":
        _fail("only a first-wave 666DEV-owned workstream can execute.")
    task = next((item for item in proposal["workstreams"]
                 if item["id"] == workstream_id), None)
    if (task is None or task["evidence_status"] != "VERIFIZIERT"
            or task["depends_on"] or task["source_commit"] != reviewed["source_revision"]):
        _fail("workstream source, evidence or dependency is unverified.")
    project_id = proposal["project_id"]
    state = rehydrate(project_id, initialize_demo=False)
    profile, source = state["profile"], state["source"]
    revision = state["revision"]["commit"]
    if (native is None or native.get("source_commit") != revision
            or reviewed["source_revision"] != revision
            or not HEX40.fullmatch(revision)):
        _fail("native LiveCircle or checkout revision changed.")
    if not clean_source(source) or unresolved_conflicts(source):
        _fail("project source is dirty or conflicted.")
    candidate_path = _safe_candidate_path(state["project_dir"], candidate_relative)
    raw = candidate_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_candidate_sha256:
        _fail("candidate content digest mismatch.")
    try:
        candidate = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise DevhubError("CONFLICT_QUARANTINE: invalid candidate JSON.") from exc
    if not isinstance(candidate, dict) or (candidate.get("schema_version") != 1
            or candidate.get("project_id") != project_id
            or candidate.get("base_commit") != revision
            or candidate.get("status") != "VORGESCHLAGEN"):
        _fail("candidate identity, base or state is invalid.")
    patches = candidate.get("patches")
    if (not isinstance(patches, list) or not 1 <= len(patches) <= 40
            or any(not isinstance(p, dict) or set(p) != {"path", "content"}
                   or not isinstance(p["path"], str) or not isinstance(p["content"], str)
                   for p in patches)):
        _fail("candidate patch entries are malformed.")
    paths = [p["path"] for p in patches]
    if len(paths) != len(set(paths)) or not set(paths) <= set(task["scope"]):
        _fail("patch paths exceed the explicitly reviewed workstream scope.")
    for path in paths:
        allowed_path(profile, source, path)

    # apply_candidate uses existing native, detached, ignored worktree and its
    # profile-scoped write checks. Never patches productive source or Current.
    worktree = apply_candidate(profile, source, candidate)
    repo_root = Path(git(source, "rev-parse", "--show-toplevel")).resolve()
    isolated_source = (worktree / source.resolve().relative_to(repo_root)).resolve()
    if not isolated_source.is_relative_to(worktree.resolve()):
        _fail("worktree source path escaped isolation.")
    checked = {}
    for patch in patches:
        target = allowed_path(profile, isolated_source, patch["path"])
        current = target.read_text(encoding="utf-8")
        if current != patch["content"]:
            _fail("candidate file readback differs.")
        checked[patch["path"]] = hashlib.sha256(target.read_bytes()).hexdigest()
    changed = git(worktree, "diff", "--name-only", "--").splitlines()
    expected_changed = {(source.resolve().relative_to(repo_root) / p).as_posix()
                        for p in paths}
    if set(changed) != expected_changed:
        _fail("Git worktree diff does not match approved file set.")
    git(worktree, "diff", "--check", "--")
    if git(source, "rev-parse", "HEAD") != revision or not clean_source(source):
        _fail("native source changed during isolated operation.")

    # Only existing profile-declared build steps enter native zero-cost
    # enforcement. Unknown build/start costs are blocked before execution.
    builds = run_acceptance(profile, isolated_source, revision, kind="build",
                            source_kind="isolated_candidate")
    build_ok = all(item["status"] == "VERIFIZIERT" for item in builds)
    receipt_id = hashlib.sha256(
        (project_id + ":" + workstream_id + ":" + revision + ":" + digest).encode()
    ).hexdigest()[:24]
    receipts = (WORK / "codeforge-receipts" / project_id).resolve()
    if not receipts.is_relative_to(WORK.resolve()):
        _fail("receipt store outside ignored native work directory.")
    destination = receipts / (receipt_id + ".json")
    if destination.exists():
        _fail("receipt already exists; repeat execution is not authorized.")
    receipt = {
        "schema": SCHEMA, "authority": "666DEV", "receipt_id": receipt_id,
        "project_id": project_id, "workstream_id": workstream_id,
        "source_commit": revision, "candidate_sha256": digest,
        "candidate_path": candidate_relative, "worktree": str(worktree),
        "changed_file_sha256": checked, "build_evidence": builds,
        "isolated_patch_applied": True, "readback_verified": True,
        "status": "PARTIAL" if build_ok else "WRITE_BLOCKED",
        "local_build_verified": build_ok, "tests_verified": False,
        "github_write_verified": False, "plugin_host_verified": False,
        "remote_peer_executed": False, "current_updated": False,
        "publication_authorized": False,
        "next_step": "Review the isolated diff and run a separately authorized native regression / draft PR.",
    }
    atomic_json(destination, receipt)
    if read_json(destination) != receipt:
        _fail("receipt readback failed.")
    return {**receipt, "receipt_path": str(destination)}
