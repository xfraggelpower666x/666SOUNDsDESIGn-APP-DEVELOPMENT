from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile
import tomllib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registry" / "projects.json"
WORK = ROOT / ".work"
STATUSES = {
    "VERIFIZIERT", "ABGELEITET", "VORGESCHLAGEN", "OFFEN", "BLOCKIERT",
    "PARTIAL", "WRITE_BLOCKED", "READBACK_PENDING", "CONFLICT_QUARANTINE",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class DevhubError(Exception):
    """Expected, user-facing workflow error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DevhubError(f"Cannot read valid JSON at {path}: {exc}") from exc


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def project_entries() -> dict[str, str]:
    registry = read_json(REGISTRY)
    if registry.get("schema_version") != 1 or not isinstance(registry.get("projects"), dict):
        raise DevhubError("Registry schema is invalid.")
    return registry["projects"]


def project_profile(project_id: str) -> tuple[dict[str, Any], Path]:
    if not ID_RE.fullmatch(project_id):
        raise DevhubError(f"Invalid project ID: {project_id}")
    entries = project_entries()
    profile_rel = entries.get(project_id)
    if not profile_rel:
        raise DevhubError(f"Unknown project ID: {project_id}")
    profile_path = (ROOT / profile_rel).resolve()
    if not profile_path.is_relative_to(ROOT.resolve()):
        raise DevhubError("Registry profile path escapes the repository.")
    profile = read_json(profile_path)
    if profile.get("id") != project_id:
        raise DevhubError(f"Profile ID mismatch for {project_id}.")
    return profile, profile_path.parent


def git(checkout: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(checkout), *args],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise DevhubError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def ensure_linked_demo() -> Path:
    """Create the ignored, local linked checkout from the tracked demo fixture."""
    checkout = WORK / "checkouts" / "demo-linked"
    if (checkout / ".git").exists():
        return checkout.resolve()
    source = ROOT / "tests" / "fixtures" / "linked-demo"
    checkout.parent.mkdir(parents=True, exist_ok=True)
    checkout.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if path.is_file():
            target = checkout / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    git(checkout, "init", "-q")
    git(checkout, "config", "user.email", "666dev@example.invalid")
    git(checkout, "config", "user.name", "666DEV demo")
    git(checkout, "add", ".")
    git(checkout, "commit", "-qm", "Initial linked demonstration")
    git(checkout, "branch", "-M", "main")
    return checkout.resolve()


def resolve_source(profile: dict[str, Any]) -> Path:
    mode = profile["source_mode"]
    if mode == "monorepo":
        source = (ROOT / profile["source_path"]).resolve()
        if not source.is_relative_to(ROOT.resolve()):
            raise DevhubError("Monorepo source path escapes repository.")
        return source
    config = read_json(WORK / "config.json") if (WORK / "config.json").exists() else {}
    configured = config.get("checkouts", {}).get(profile["id"])
    if not configured and profile["id"] == "demo-linked":
        return ensure_linked_demo()
    if not configured:
        raise DevhubError("Linked checkout missing; set .work/config.json with its local path.")
    source = Path(configured).expanduser().resolve()
    if not (source / ".git").exists():
        raise DevhubError(f"Linked checkout is not a Git repository: {source}")
    return source


def resolve_revision(profile: dict[str, Any], source: Path) -> dict[str, str]:
    commit = git(source, "rev-parse", "HEAD")
    branch = git(source, "branch", "--show-current")
    mode = profile["source_mode"]
    expected_ref = profile.get("expected_ref", "HEAD")
    expected_repo = profile.get("expected_repository")
    if mode == "linked":
        identity_path = source / "identity.json"
        identity = read_json(identity_path).get("repository") if identity_path.exists() else None
        if expected_repo and identity and identity != expected_repo:
            raise DevhubError(f"Linked repository identity mismatch: expected {expected_repo}, got {identity}")
        remote = git(source, "config", "--get", "remote.origin.url") if subprocess.run(
            ["git", "-C", str(source), "config", "--get", "remote.origin.url"],
            capture_output=True,
        ).returncode == 0 else None
        if expected_repo and not identity and remote and remote != expected_repo:
            raise DevhubError(f"Linked repository identity mismatch: expected {expected_repo}, got {remote}")
        if expected_repo and not identity and not remote:
            raise DevhubError("Linked repository identity cannot be verified: origin remote is missing.")
    ref_commit = git(source, "rev-parse", "--verify", f"{expected_ref}^{{commit}}")
    if ref_commit != commit:
        raise DevhubError(f"Expected ref {expected_ref} resolves to {ref_commit}, but HEAD is {commit}.")
    return {"commit": commit, "branch": branch or "DETACHED", "expected_ref": expected_ref}


def allowed_path(profile: dict[str, Any], source: Path, candidate: str | Path) -> Path:
    raw = Path(candidate)
    windows_path = PureWindowsPath(str(candidate))
    if windows_path.is_absolute() or windows_path.drive:
        raise DevhubError(f"WRITE_BLOCKED: Windows absolute path is not a project-relative path: {candidate}")
    if raw.is_absolute():
        target = raw.resolve()
    else:
        target = (source / raw).resolve()
    roots = [source / path for path in profile.get("writable_paths", [])]
    if not any(target.is_relative_to(root.resolve()) for root in roots):
        raise DevhubError(f"WRITE_BLOCKED: path is outside project write scope: {target}")
    return target


def current_file(project_dir: Path) -> Path:
    return project_dir / "state" / "current.json"


def checkpoint_file(project_dir: Path, checkpoint_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9-]+", checkpoint_id):
        raise DevhubError("Invalid checkpoint reference.")
    return project_dir / "state" / "checkpoints" / f"{checkpoint_id}.json"


@contextmanager
def project_lock(project_id: str):
    lock_path = WORK / "locks" / f"{project_id}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise DevhubError(f"WRITE_BLOCKED: project lock already exists: {lock_path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as lock:
            lock.write(f"pid={os.getpid()}\n")
            lock.flush()
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def make_evidence(kind: str, source: str, revision: str, environment: str, observed: str,
                  status: str = "VERIFIZIERT") -> dict[str, Any]:
    return {
        "status": status, "evidence_type": kind, "source": source, "commit": revision,
        "environment": environment, "observed": observed,
    }


def load_current(profile: dict[str, Any], project_dir: Path) -> dict[str, Any] | None:
    path = current_file(project_dir)
    if not path.exists():
        return None
    current = read_json(path)
    checkpoint = checkpoint_file(project_dir, current["checkpoint_id"])
    if not checkpoint.exists():
        raise DevhubError(f"Current points to missing checkpoint: {current['checkpoint_id']}")
    body = read_json(checkpoint)
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if current.get("sha256") != digest or body.get("project_id") != profile["id"]:
        raise DevhubError("Current/checkpoint integrity mismatch; quarantined for recovery.")
    return {"pointer": current, "checkpoint": body}


def checkpoint(profile: dict[str, Any], project_dir: Path, revision: str, task: str,
               evidence: list[dict[str, Any]], open_work: list[dict[str, Any]], scope: list[str]) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    state_dir = project_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    with project_lock(profile["id"]):
        checkpoint_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        current_path = current_file(project_dir)
        prior = read_json(current_path) if current_path.exists() else None
        payload = {
            "schema_version": 1, "project_id": profile["id"], "checkpoint_id": checkpoint_id,
            "task": task, "base_commit": prior.get("commit") if prior else revision,
            "observed_head": revision, "allowed_scope": scope,
            "return_anchor": prior.get("checkpoint_id") if prior else None,
            "affected_files": [], "results": evidence, "open_work": open_work,
            "created_at": utc_now(),
        }
        destination = checkpoint_file(project_dir, checkpoint_id)
        atomic_json(destination, payload)
        pointer = {"schema_version": 1, "project_id": profile["id"], "checkpoint_id": checkpoint_id,
                   "commit": revision, "updated_at": utc_now(),
                   "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
        actual = read_json(current_path) if current_path.exists() else None
        if actual != prior:
            raise DevhubError("CONFLICT_QUARANTINE: Current changed during update; checkpoint retained.")
        atomic_json(current_path, pointer)
        if read_json(current_path) != pointer:
            raise DevhubError("Current readback failed.")
        return payload


def run_acceptance(profile: dict[str, Any], source: Path, revision: str) -> list[dict[str, Any]]:
    evidence = []
    for configured in profile.get("test_commands", []):
        command = shlex.split(configured, posix=os.name != "nt")
        if command and Path(command[0]).name.lower() in {"python", "python3", "python.exe"}:
            command[0] = sys.executable
        try:
            result = subprocess.run(command, cwd=source, capture_output=True, text=True,
                                    timeout=120, check=False)
            output = (result.stdout + result.stderr).strip()
            status = "VERIFIZIERT" if result.returncode == 0 else "BLOCKIERT"
            observed = f"exit={result.returncode}; {output[-4000:]}"
        except (OSError, subprocess.TimeoutExpired) as exc:
            status = "BLOCKIERT"
            observed = f"{type(exc).__name__}: {exc}"
        evidence.append(make_evidence("test", configured, revision,
                                      f"{sys.platform}; Python {sys.version.split()[0]}",
                                      observed, status))
    return evidence


def apply_candidate(profile: dict[str, Any], source: Path, candidate: dict[str, Any]) -> Path:
    if candidate.get("project_id") != profile["id"]:
        raise DevhubError("Candidate belongs to another project.")
    revision = resolve_revision(profile, source)
    if candidate.get("base_commit") != revision["commit"]:
        raise DevhubError("Candidate base commit differs from the verified HEAD.")
    patches = candidate.get("patches")
    if not isinstance(patches, list) or not patches:
        raise DevhubError("Candidate has no patch payload; no worktree was created.")
    repo_root = Path(git(source, "rev-parse", "--show-toplevel")).resolve()
    source_from_root = source.resolve().relative_to(repo_root)
    worktree = WORK / "worktrees" / profile["id"] / candidate.get("candidate_id", revision["commit"][:12])
    if worktree.exists():
        raise DevhubError(f"WRITE_BLOCKED: candidate worktree already exists: {worktree}")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    git(repo_root, "worktree", "add", "--detach", str(worktree), revision["commit"])
    try:
        for patch in patches:
            relative = patch.get("path")
            content = patch.get("content")
            if not isinstance(relative, str) or not isinstance(content, str):
                raise DevhubError("Patch entries require string path and content.")
            allowed_path(profile, source, relative)
            target = (worktree / source_from_root / relative).resolve()
            if not target.is_relative_to(worktree.resolve()):
                raise DevhubError("WRITE_BLOCKED: patch target escapes isolated worktree.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return worktree
    except Exception:
        subprocess.run(["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree)],
                       capture_output=True, check=False)
        raise


def rehydrate(project_id: str) -> dict[str, Any]:
    profile, project_dir = project_profile(project_id)
    source = resolve_source(profile)
    revision = resolve_revision(profile, source)
    current = load_current(profile, project_dir)
    if current and current["checkpoint"]["observed_head"] != revision["commit"]:
        current["revision_status"] = "PARTIAL"
        current["revision_note"] = "HEAD differs from checkpoint; affected work requires re-audit."
    elif current:
        current["revision_status"] = "VERIFIZIERT"
    return {"profile": profile, "project_dir": project_dir, "source": source,
            "revision": revision, "current": current}


def python_graph(source: Path, profile: dict[str, Any], revision: str) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    py_files = sorted(source.rglob("*.py"))
    for path in py_files:
        if any(part in {".git", ".work", "__pycache__"} for part in path.parts):
            continue
        rel = path.relative_to(source).as_posix()
        nodes.append({"id": rel, "kind": "module", "source": rel, "revision": revision})
        try:
            import ast
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports = [node.module]
                else:
                    continue
                for module in imports:
                    target = module.replace(".", "/") + ".py"
                    if not (source / target).exists() and (source / "src" / target).exists():
                        target = f"src/{target}"
                    if (source / target).exists():
                        edges.append({"from": rel, "to": target, "direction": "imports",
                                      "revision": revision, "evidence": "VERIFIZIERT",
                                      "source": rel})
        except (SyntaxError, UnicodeDecodeError):
            continue
    for entry in profile.get("entry_points", []):
        nodes.append({"id": entry, "kind": "entry_point", "source": "project.json",
                      "revision": revision})
        for build_file in profile.get("build_contracts", []):
            nodes.append({"id": build_file, "kind": "build_contract", "source": "project.json",
                          "revision": revision})
            edges.append({"from": entry, "to": build_file, "direction": "declares",
                          "revision": revision, "evidence": "VERIFIZIERT", "source": "project.json"})
            contract_path = source / build_file
            if contract_path.suffix == ".toml" and contract_path.exists():
                try:
                    contract = tomllib.loads(contract_path.read_text(encoding="utf-8"))
                    scripts = contract.get("project", {}).get("scripts", {})
                    for target in scripts.values():
                        module = target.split(":", 1)[0].replace(".", "/") + ".py"
                        if not (source / module).exists() and (source / "src" / module).exists():
                            module = f"src/{module}"
                        if (source / module).exists():
                            edges.append({"from": build_file, "to": module, "direction": "targets",
                                          "revision": revision, "evidence": "VERIFIZIERT",
                                          "source": build_file})
                except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                    pass
        for test_path in profile.get("test_paths", []):
            nodes.append({"id": test_path, "kind": "test", "source": "project.json",
                          "revision": revision})
            edges.append({"from": entry, "to": test_path, "direction": "validated_by",
                          "revision": revision, "evidence": "ABGELEITET", "source": "project.json"})
            for build_file in profile.get("build_contracts", []):
                edges.append({"from": build_file, "to": test_path, "direction": "checked_by",
                              "revision": revision, "evidence": "ABGELEITET", "source": "project.json"})
    return {"revision": revision, "nodes": nodes, "edges": edges,
            "dynamic_bindings": {"status": "OFFEN", "reason": "Dynamic Python imports are not statically resolved."}}


def inspect_project(project_id: str) -> dict[str, Any]:
    state = rehydrate(project_id)
    current = state["current"]
    last = current["checkpoint"] if current else None
    return {
        "id": project_id, "name": state["profile"]["name"], "source_mode": state["profile"]["source_mode"],
        "demo": state["profile"].get("demo", False), "commit": state["revision"]["commit"],
        "current": last, "last_session": last.get("created_at") if last else None,
        "next_step": (last.get("open_work") or [{}])[0].get("step", "Run SYSTEMSTART for initial verification") if last else
                     "Run SYSTEMSTART to create the first checkpoint",
        "revision_status": current.get("revision_status", "OFFEN") if current else "OFFEN",
    }


def validate_zip(archive: Path, manifest: dict[str, str]) -> list[str]:
    errors = []
    with zipfile.ZipFile(archive) as bundle:
        for name, digest in manifest.items():
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                errors.append(f"Unsafe ZIP entry: {name}")
                continue
            try:
                actual = hashlib.sha256(bundle.read(name)).hexdigest()
                if actual != digest:
                    errors.append(f"Hash mismatch: {name}")
            except KeyError:
                errors.append(f"Missing ZIP entry: {name}")
    return errors


def freeze_project(profile: dict[str, Any], source: Path) -> tuple[Path, dict[str, str]]:
    source = source.resolve()
    archive = WORK / "freezes" / profile["id"] / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.is_symlink() or ".git" in path.parts:
                continue
            relative = path.relative_to(source).as_posix()
            payload = path.read_bytes()
            manifest[relative] = hashlib.sha256(payload).hexdigest()
            bundle.writestr(relative, payload)
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    failures = validate_zip(archive, manifest)
    if failures:
        archive.unlink(missing_ok=True)
        raise DevhubError("Freeze ZIP verification failed: " + "; ".join(failures))
    return archive, manifest


def dashboard_data() -> dict[str, Any]:
    projects = []
    for project_id in sorted(project_entries()):
        try:
            state = rehydrate(project_id)
            profile = state["profile"]
            projects.append({
                **inspect_project(project_id),
                "graph": python_graph(state["source"], profile, state["revision"]["commit"]),
                "evidence": state["current"]["checkpoint"]["results"] if state["current"] else [],
                "history": sorted(
                    path.name for path in
                    (state["project_dir"] / "state" / "checkpoints").glob("*.json")
                ),
                "recovery_anchor": state["current"]["checkpoint"].get("return_anchor") if state["current"] else None,
            })
        except DevhubError as exc:
            projects.append({"id": project_id, "error": str(exc), "evidence": [], "graph": {"nodes": [], "edges": []}})
    return {"generated_at": utc_now(), "projects": projects,
            "providers": {"github": "READBACK_PENDING", "ci": "OFFEN", "target_host": "OFFEN"}}
