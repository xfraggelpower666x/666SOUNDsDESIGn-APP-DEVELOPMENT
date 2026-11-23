"""Explicit 666DEV-only draft PR transport for a verified isolated R10 receipt.

Never auto-merge, update Current, push to foreign owners or reuse credentials.
Uses the existing Git/gh provider; GitHub availability is a separate host gate.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ..core import DevhubError, ROOT, WORK, atomic_json, git, read_json
from ..repo_mind import REPOSITORY, gh
from .cost_guard import evaluate

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
RECEIPT_ID = re.compile(r"^[0-9a-f]{24}$")
PROJECT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,100}$")
TARGET_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,200}$")


def _blocked(reason: str) -> None:
    raise DevhubError("WRITE_BLOCKED: " + reason)


def publish_draft(*, project_id: str, receipt_id: str, expected_head: str,
                  target_branch: str, confirmation: str) -> dict:
    """Direct CLI consent only. Safe draft-PR transport of ONE R10 666DEV receipt."""
    if confirmation != "CONFIRM_DRAFT_PR":
        _blocked("explicit confirmation required; never publish from a peer handoff.")
    if not (isinstance(project_id, str) and PROJECT_ID.fullmatch(project_id)
            and isinstance(receipt_id, str) and RECEIPT_ID.fullmatch(receipt_id)
            and isinstance(expected_head, str) and FULL_SHA.fullmatch(expected_head)
            and isinstance(target_branch, str) and TARGET_REF.fullmatch(target_branch)
            and ".." not in target_branch and "//" not in target_branch
            and not target_branch.endswith(("/", ".", ".lock"))):
        _blocked("invalid native project, receipt, immutable base or target.")
    receipt_path = (WORK / "codeforge-receipts" / project_id / (receipt_id + ".json")).resolve()
    root = (WORK / "codeforge-receipts").resolve()
    if (not receipt_path.is_relative_to(root) or not receipt_path.is_file()
            or receipt_path.is_symlink() or receipt_path.stat().st_size > 262144):
        _blocked("missing or unsafe local execution receipt.")
    receipt = read_json(receipt_path)
    if (receipt.get("schema") != "666dev-codeforge-execution/v1"
            or receipt.get("authority") != "666DEV"
            or receipt.get("project_id") != project_id
            or receipt.get("receipt_id") != receipt_id
            or receipt.get("source_commit") != expected_head
            or receipt.get("isolated_patch_applied") is not True
            or receipt.get("readback_verified") is not True
            or receipt.get("remote_peer_executed") is not False
            or receipt.get("github_write_verified") is not False
            or receipt.get("current_updated") is not False):
        _blocked("receipt integrity, native ownership or Git base not verified.")
    worktree = Path(receipt.get("worktree", "")).resolve()
    isolated_root = (WORK / "worktrees" / project_id).resolve()
    if not worktree.is_relative_to(isolated_root) or not worktree.is_dir():
        _blocked("receipt worktree outside native isolation.")
    # Native repository identity is resolved from the existing checkout;
    # never promote a linked or foreign repository under 666DEV authority.
    from ..core import project_profile
    profile, _ = project_profile(project_id)
    if profile.get("source_mode") != "monorepo":
        _blocked("cross-repository publication must use that owner's native tool.")
    source_prefix = Path(profile.get("source_path", ""))
    if source_prefix.is_absolute() or ".." in source_prefix.parts:
        _blocked("untrusted project source root.")
    changed = receipt.get("changed_file_sha256")
    if not isinstance(changed, dict) or not changed:
        _blocked("empty or invalid approved diff.")
    for path, expected_digest in changed.items():
        if (not isinstance(path, str) or not path
                or not isinstance(expected_digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_digest)):
            _blocked("invalid changed-file evidence.")
        target = (worktree / source_prefix / path).resolve()
        if not target.is_relative_to((worktree / source_prefix).resolve()) or not target.is_file():
            _blocked("unreadable candidate file.")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected_digest:
            _blocked("candidate file changed since isolated readback.")
    if git(worktree, "rev-parse", "HEAD") != expected_head:
        _blocked("worktree HEAD changed since execution.")
    if git(ROOT, "rev-parse", "HEAD") != expected_head:
        _blocked("native checkout HEAD no longer matches candidate base.")
    origin = git(ROOT, "remote", "get-url", "--push", "origin").removesuffix(".git")
    if origin not in {f"https://github.com/{REPOSITORY}", f"git@github.com:{REPOSITORY}"}:
        _blocked("origin is not native 666DEV GitHub repository.")
    remote_target = f"refs/heads/{target_branch}"
    if git(ROOT, "ls-remote", "--refs", "origin", remote_target).split() != [expected_head, remote_target]:
        _blocked("remote target branch drift; publication requires exact-base readback.")
    # Query repo privacy before the zero-additional-cost gate.
    metadata = json.loads(gh(ROOT, "repo", "view", REPOSITORY, "--json", "isPrivate"))
    if metadata.get("isPrivate") is not False:
        _blocked("zero additional cost cannot be verified for private/unreadable GitHub repo.")
    cost = evaluate("EXTERNAL_ACTION", "VERIFIED_FREE",
                    evidence={"verified_zero_cost": True,
                              "source": "verified public GitHub repository; standard git/PR API"})
    if not cost["allowed"]:
        _blocked("GitHub write cost not authorized.")
    branch = "666codeforge/r10-" + receipt_id
    branch_ref = "refs/heads/" + branch
    if git(ROOT, "ls-remote", "--refs", "origin", branch_ref):
        _blocked("draft branch already exists; no automatic overwrite or replay.")

    expected_paths = {(source_prefix / path).as_posix() for path in changed}
    actual = set(git(worktree, "diff", "--name-only", "--").splitlines())
    if actual != expected_paths:
        _blocked("candidate diff does not equal approved path set.")
    git(worktree, "diff", "--check", "--")
    git(worktree, "add", "--", *sorted(expected_paths))
    if set(git(worktree, "diff", "--cached", "--name-only").splitlines()) != expected_paths:
        _blocked("staged paths changed during publication.")
    git(worktree, "diff", "--cached", "--check")
    git(worktree, "commit", "-m", "666DEV R10 isolated CodeForge candidate " + receipt_id)
    candidate_commit = git(worktree, "rev-parse", "HEAD")
    if git(ROOT, "ls-remote", "--refs", "origin", remote_target).split() != [expected_head, remote_target]:
        _blocked("remote base changed before push.")
    git(worktree, "push", "origin", f"HEAD:{branch_ref}")
    pushed = git(ROOT, "ls-remote", "--refs", "origin", branch_ref).split()
    if pushed != [candidate_commit, branch_ref]:
        return {"status": "READBACK_PENDING", "candidate_commit": candidate_commit,
                "reason": "Remote branch push not confirmed."}
    url = gh(ROOT, "pr", "create", "--repo", REPOSITORY, "--draft",
             "--base", target_branch, "--head", branch,
             "--title", "666DEV R10 · isolated CodeForge candidate " + receipt_id,
             "--body", "Explicit 666DEV-only candidate. Native baseline: " + expected_head
             + ". Isolated file SHA readback verified. No merge, foreign write or Current promotion."
             + " Candidate CI, Windows and plugin host acceptance remain separate.")
    remote_pr = json.loads(gh(ROOT, "pr", "view", branch, "--repo", REPOSITORY,
                              "--json", "isDraft,headRefOid,baseRefName,url"))
    confirmed = (remote_pr.get("isDraft") is True
                 and remote_pr.get("headRefOid") == candidate_commit
                 and remote_pr.get("baseRefName") == target_branch
                 and git(ROOT, "ls-remote", "--refs", "origin", remote_target).split()
                     == [expected_head, remote_target])
    result = {
        "schema": "666dev-codeforge-draft-publication/v1",
        "status": "VERIFIZIERT" if confirmed else "READBACK_PENDING",
        "authority": "666DEV", "receipt_id": receipt_id, "project_id": project_id,
        "base_commit": expected_head, "candidate_commit": candidate_commit,
        "draft_branch": branch, "target_branch": target_branch,
        "draft_pr": remote_pr.get("url") if confirmed else url,
        "github_write_verified": bool(confirmed),
        "ci_verified": False, "host_verified": False, "current_updated": False,
        "foreign_write": False, "auto_merge": False,
    }
    evidence_path = receipt_path.with_name("DRAFT_" + receipt_id + ".json")
    atomic_json(evidence_path, result)
    if read_json(evidence_path) != result:
        _blocked("publication receipt readback failed.")
    return result
