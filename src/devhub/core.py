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
    if (not isinstance(registry, dict) or registry.get("schema_version") != 1
            or not isinstance(registry.get("projects"), dict)):
        raise DevhubError("Registry schema is invalid.")
    projects = registry["projects"]
    if any(not isinstance(project_id, str) or not ID_RE.fullmatch(project_id)
           or not isinstance(profile_path, str) for project_id, profile_path in projects.items()):
        raise DevhubError("Registry contains an invalid project ID or profile path.")
    return projects


def project_profile(project_id: str) -> tuple[dict[str, Any], Path]:
    if not ID_RE.fullmatch(project_id):
        raise DevhubError(f"Invalid project ID: {project_id}")
    entries = project_entries()
    profile_rel = entries.get(project_id)
    if not profile_rel:
        raise DevhubError(f"Unknown project ID: {project_id}")
    if not isinstance(profile_rel, str):
        raise DevhubError(f"Invalid registry profile path for {project_id}.")
    profile_windows_path = PureWindowsPath(profile_rel)
    profile_posix_path = PurePosixPath(profile_rel)
    if (profile_windows_path.is_absolute() or profile_windows_path.drive
            or profile_posix_path.is_absolute() or ".." in profile_posix_path.parts
            or "\\" in profile_rel):
        raise DevhubError("Registry profile path must be a repository-relative POSIX path.")
    profile_path = (ROOT / profile_rel).resolve()
    if not profile_path.is_relative_to(ROOT.resolve()):
        raise DevhubError("Registry profile path escapes the repository.")
    profile = read_json(profile_path)
    if not isinstance(profile, dict):
        raise DevhubError(f"Project profile for {project_id} must be a JSON object.")
    if profile.get("id") != project_id:
        raise DevhubError(f"Profile ID mismatch for {project_id}.")
    if profile.get("source_mode") not in {"monorepo", "linked"}:
        raise DevhubError(f"Unsupported source mode for {project_id}.")
    required = ("name", "application_type", "platforms", "entry_points", "language_files",
                "build_contracts", "test_paths", "writable_paths", "build_commands",
                "test_commands", "acceptance")
    if any(key not in profile for key in required):
        raise DevhubError(f"Project profile {project_id} is missing required contract fields.")
    if not isinstance(profile.get("name"), str) or not profile["name"].strip():
        raise DevhubError(f"Project profile {project_id} requires a display name.")
    if not isinstance(profile.get("platforms"), list) or not profile["platforms"]:
        raise DevhubError(f"Project profile {project_id} requires target platforms.")
    if not isinstance(profile.get("acceptance"), list) or not profile["acceptance"]:
        raise DevhubError(f"Project profile {project_id} requires acceptance criteria.")
    if profile.get("source_mode") == "monorepo":
        source_rel = profile.get("source_path", "")
        if not isinstance(source_rel, str):
            raise DevhubError("Monorepo source_path must be a string.")
        windows_source = PureWindowsPath(source_rel)
        posix_source = PurePosixPath(source_rel)
        if (not source_rel or windows_source.is_absolute() or windows_source.drive or posix_source.is_absolute()
                or ".." in posix_source.parts or "\\" in source_rel):
            raise DevhubError("Monorepo source path must be a repository-relative POSIX path.")
    writable_paths = profile.get("writable_paths", [])
    if not isinstance(writable_paths, list):
        raise DevhubError(f"writable_paths must be an array in profile {project_id}.")
    for writable in writable_paths:
        windows_path = PureWindowsPath(writable) if isinstance(writable, str) else PureWindowsPath()
        posix_path = PurePosixPath(writable) if isinstance(writable, str) else PurePosixPath()
        if (not isinstance(writable, str) or "\\" in writable or windows_path.is_absolute()
                or windows_path.drive or posix_path.is_absolute() or ".." in posix_path.parts):
            raise DevhubError(f"Invalid writable path in profile {project_id}: {writable}")
    for key in ("entry_points", "language_files", "build_contracts", "test_paths"):
        values = profile.get(key, [])
        if not isinstance(values, list) or any(
            not isinstance(value, str) or "\\" in value or PureWindowsPath(value).is_absolute()
            or PureWindowsPath(value).drive or PurePosixPath(value).is_absolute()
            or ".." in PurePosixPath(value).parts
            for value in values
        ):
            raise DevhubError(f"Invalid {key} path list in profile {project_id}.")
    declarations = profile.get("test_dependencies", {})
    if not isinstance(declarations, dict) or any(
        test not in profile["test_paths"] or not isinstance(paths, list) or not paths
        or any(not isinstance(path, str) or path in {"", "."} or "\\" in path
               or PureWindowsPath(path).drive or PurePosixPath(path).is_absolute()
               or ".." in PurePosixPath(path).parts for path in paths)
        for test, paths in declarations.items()
    ):
        raise DevhubError(f"Invalid test_dependencies in profile {project_id}.")
    if not isinstance(profile.get("expected_ref"), str) or not profile["expected_ref"]:
        raise DevhubError(f"Profile {project_id} requires expected_ref.")
    for key in ("build_commands", "test_commands", "start_commands"):
        commands = profile.get(key, [])
        if not isinstance(commands, list) or any(
            not ((isinstance(command, str) and command.strip())
                 or (isinstance(command, list) and command
                     and all(isinstance(arg, str) for arg in command) and command[0].strip()))
            for command in commands
        ):
            raise DevhubError(f"Invalid {key} in profile {project_id}.")
    if profile["source_mode"] == "linked" and (
        not isinstance(profile.get("expected_repository"), str) or not profile["expected_repository"]
    ):
        raise DevhubError(f"Linked profile {project_id} requires expected_repository.")
    if not isinstance(profile.get("console_entrypoints", {}), dict) or any(
        not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
        or not isinstance(target, str) or
        not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_.]*", target)
        for name, target in profile.get("console_entrypoints", {}).items()
    ):
        raise DevhubError(f"Invalid console entry point contract in profile {project_id}.")
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


def resolve_source(profile: dict[str, Any], *, initialize_demo: bool = True) -> Path:
    mode = profile["source_mode"]
    if mode == "monorepo":
        source = (ROOT / profile["source_path"]).resolve()
        if not source.is_relative_to(ROOT.resolve()):
            raise DevhubError("Monorepo source path escapes repository.")
        return source
    config = read_json(WORK / "config.json") if (WORK / "config.json").exists() else {}
    configured = config.get("checkouts", {}).get(profile["id"])
    if not configured and profile["id"] == "demo-linked":
        if initialize_demo:
            return ensure_linked_demo()
        checkout = WORK / "checkouts" / "demo-linked"
        if (checkout / ".git").exists():
            return checkout.resolve()
    if not configured:
        raise DevhubError("Linked checkout missing; set .work/config.json with its local path.")
    if not isinstance(configured, str):
        raise DevhubError("Linked checkout path must be a string in .work/config.json.")
    source = Path(configured).expanduser().resolve()
    if not (source / ".git").exists():
        raise DevhubError(f"Linked checkout is not a Git repository: {source}")
    return source


def validate_profile_source(profile: dict[str, Any], source: Path) -> None:
    source = source.resolve()
    for key in ("entry_points", "language_files", "build_contracts", "test_paths"):
        for relative in profile.get(key, []):
            target = (source / relative).resolve()
            if not target.is_relative_to(source):
                raise DevhubError(f"Profile {key} path escapes project source: {relative}")
            if not target.is_file():
                raise DevhubError(f"Profile {key} file is missing: {relative}")
    for relative in profile.get("writable_paths", []):
        target = (source / relative).resolve()
        if not target.is_relative_to(source):
            raise DevhubError(f"WRITE_BLOCKED: profile write path escapes project source: {relative}")


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
        if expected_repo and remote and remote != expected_repo:
            raise DevhubError(f"Linked repository identity mismatch: expected {expected_repo}, got {remote}")
        if expected_repo and not identity and not remote:
            raise DevhubError("Linked repository identity cannot be verified: origin remote is missing.")
    ref_commit = git(source, "rev-parse", "--verify", "--end-of-options",
                     f"{expected_ref}^{{commit}}")
    if ref_commit != commit:
        raise DevhubError(f"Expected ref {expected_ref} resolves to {ref_commit}, but HEAD is {commit}.")
    return {"commit": commit, "branch": branch or "DETACHED", "expected_ref": expected_ref}


def allowed_path(profile: dict[str, Any], source: Path, candidate: str | Path) -> Path:
    raw = Path(candidate)
    windows_path = PureWindowsPath(str(candidate))
    if windows_path.is_absolute() or windows_path.drive or "\\" in str(candidate):
        raise DevhubError(f"WRITE_BLOCKED: Windows absolute path is not a project-relative path: {candidate}")
    if raw.is_absolute():
        target = raw.resolve()
    else:
        target = (source / raw).resolve()
    source_root = source.resolve()
    roots = [(source_root / path).resolve() for path in profile.get("writable_paths", [])]
    if any(not root.is_relative_to(source_root) for root in roots):
        raise DevhubError("WRITE_BLOCKED: profile write root escapes project source.")
    if not any(target.is_relative_to(root) for root in roots):
        raise DevhubError(f"WRITE_BLOCKED: path is outside project write scope: {target}")
    return target


def state_file(project_dir: Path, *parts: str) -> Path:
    state = project_dir / "state"
    path = state.joinpath(*parts)
    resolved = path.resolve()
    if state.is_symlink() or path.is_symlink() or not resolved.is_relative_to(state):
        raise DevhubError("WRITE_BLOCKED: project state path escapes its directory.")
    return resolved


def current_file(project_dir: Path) -> Path:
    return state_file(project_dir, "current.json")


def checkpoint_file(project_dir: Path, checkpoint_id: str) -> Path:
    if not isinstance(checkpoint_id, str) or not re.fullmatch(r"[a-zA-Z0-9-]+", checkpoint_id):
        raise DevhubError("Invalid checkpoint reference.")
    return state_file(project_dir, "checkpoints", f"{checkpoint_id}.json")


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


def load_current(profile: dict[str, Any], project_dir: Path, *, working: bool = False) -> dict[str, Any] | None:
    path = state_file(project_dir, "working.json") if working else current_file(project_dir)
    if not path.exists():
        return None
    pointer = read_json(path)
    if not isinstance(pointer, dict):
        raise DevhubError("Invalid project state pointer.")
    checkpoint = checkpoint_file(project_dir, pointer.get("checkpoint_id"))
    if not checkpoint.is_file():
        raise DevhubError("State pointer references a missing checkpoint.")
    payload = checkpoint.read_bytes()
    try:
        body = json.loads(payload)
    except (ValueError, UnicodeError) as exc:
        raise DevhubError("Cannot decode referenced checkpoint.") from exc
    if (not isinstance(body, dict) or pointer.get("schema_version") != 1
            or pointer.get("project_id") != profile["id"]
            or pointer.get("sha256") != hashlib.sha256(payload).hexdigest()
            or body.get("project_id") != profile["id"] or body.get("schema_version") != 1
            or body.get("checkpoint_id") != pointer["checkpoint_id"]
            or pointer.get("commit") != body.get("observed_head")
            or not isinstance(body.get("results"), list) or not isinstance(body.get("open_work"), list)
            or any(not isinstance(item, dict) for item in body["results"] + body["open_work"])):
        raise DevhubError("Current/checkpoint integrity mismatch; quarantined for recovery.")
    return {"pointer": pointer, "checkpoint": body}


def checkpoint(profile: dict[str, Any], project_dir: Path, revision: str, task: str,
               evidence: list[dict[str, Any]], open_work: list[dict[str, Any]], scope: list[str],
               affected_files: list[str] | None = None, *, observed: dict[str, Any],
               publish: bool = False) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    working_path = state_file(project_dir, "working.json")
    current_path = current_file(project_dir)
    expected = {
        working_path: observed.get("working_pointer"),
        current_path: observed["current"]["pointer"] if observed["current"] else None,
    }

    def check_unchanged() -> None:
        for path, previous in expected.items():
            if (read_json(path) if path.exists() else None) != previous:
                raise DevhubError("CONFLICT_QUARANTINE: project pointer changed during the operation.")

    with project_lock(profile["id"]):
        check_unchanged()
        checkpoint_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        prior = observed["working"]
        payload = {
            "schema_version": 1, "project_id": profile["id"], "checkpoint_id": checkpoint_id,
            "task": task, "base_commit": prior["pointer"]["commit"] if prior else revision,
            "observed_head": revision, "allowed_scope": scope,
            "return_anchor": prior["pointer"]["checkpoint_id"] if prior else None,
            "affected_files": affected_files or [], "results": evidence, "open_work": open_work,
            "created_at": utc_now(),
        }
        destination = checkpoint_file(project_dir, checkpoint_id)
        atomic_json(destination, payload)
        if read_json(destination) != payload:
            raise DevhubError("Checkpoint readback failed.")
        pointer = {"schema_version": 1, "project_id": profile["id"], "checkpoint_id": checkpoint_id,
                   "commit": revision, "updated_at": utc_now(),
                   "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
        check_unchanged()
        if observed.get("source") and resolve_revision(profile, observed["source"])["commit"] != revision:
            raise DevhubError("CONFLICT_QUARANTINE: repository HEAD changed during the operation.")
        if publish and not clean_source(observed["source"]):
            raise DevhubError("WRITE_BLOCKED: project source changed during acceptance.")
        path = current_path if publish else working_path
        atomic_json(path, pointer)
        if read_json(path) != pointer:
            raise DevhubError("Project pointer readback failed.")
        return payload


def clean_source(source: Path) -> bool:
    return not git(source, "--no-optional-locks", "status", "--porcelain",
                   "--untracked-files=all", "--", ".")


def run_acceptance(profile: dict[str, Any], source: Path, revision: str, *,
                   kind: str = "test", source_kind: str = "checkout") -> list[dict[str, Any]]:
    from .recovery import command_display, profile_fingerprint

    evidence = []
    profile_hash = profile_fingerprint(profile)

    def clean_revision() -> bool:
        try:
            return git(source, "rev-parse", "HEAD") == revision and clean_source(source)
        except DevhubError:
            return False

    key = {"test": "test_commands", "build": "build_commands", "start": "start_commands"}[kind]
    commands = profile.get(key, [])
    for configured in commands:
        display = command_display(configured)
        clean_before = source_kind == "checkout" and clean_revision()
        receipt = {"source_kind": source_kind, "profile_sha256": profile_hash,
                   "clean_revision": False, "platform": sys.platform,
                   "exit_code": None, "state": "invalid_command"}
        try:
            command = shlex.split(configured, posix=os.name != "nt") if isinstance(configured, str) else list(configured)
        except ValueError:
            command = []
        if not command:
            evidence.append(make_evidence(kind, display, revision,
                                          f"{sys.platform}; Python {sys.version.split()[0]}",
                                          "Configured acceptance command is empty.", "BLOCKIERT"))
            receipt["clean_revision"] = clean_before
            evidence[-1]["execution"] = receipt
            continue
        if command and Path(command[0]).name.lower() in {"python", "python3", "python.exe"}:
            command[0] = sys.executable
        try:
            with tempfile.TemporaryDirectory(prefix="666dev-pycache-") as cache:
                result = subprocess.run(command, cwd=source, capture_output=True, text=True,
                                        timeout=120, check=False, encoding="utf-8", errors="replace",
                                        env={**os.environ, "PYTHONPYCACHEPREFIX": cache})
            output = (result.stdout + result.stderr).strip()
            status = "VERIFIZIERT" if result.returncode == 0 else "BLOCKIERT"
            observed = f"exit={result.returncode}; {output[-4000:]}"
            receipt.update(state="completed", exit_code=result.returncode)
        except (OSError, subprocess.TimeoutExpired) as exc:
            status = "BLOCKIERT"
            receipt["state"] = "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "launch_error"
            observed = f"{type(exc).__name__}: {exc}"
        evidence.append(make_evidence(kind, display, revision,
                                      f"{sys.platform}; Python {sys.version.split()[0]}",
                                      observed, status))
        receipt["clean_revision"] = clean_before and clean_revision()
        evidence[-1]["execution"] = receipt
    if not commands:
        evidence.append(make_evidence(kind, "project.json", revision,
                                      f"{sys.platform}; Python {sys.version.split()[0]}",
                                      f"No {kind} command is configured.", "BLOCKIERT"))
    return evidence


def apply_candidate(profile: dict[str, Any], source: Path, candidate: dict[str, Any]) -> Path:
    if candidate.get("project_id") != profile["id"]:
        raise DevhubError("Candidate belongs to another project.")
    revision = resolve_revision(profile, source)
    if candidate.get("base_commit") != revision["commit"]:
        raise DevhubError("Candidate base commit differs from the verified HEAD.")
    patches = candidate.get("patches")
    if not isinstance(patches, list) or not patches or any(not isinstance(patch, dict) for patch in patches):
        raise DevhubError("Candidate has no patch payload; no worktree was created.")
    candidate_id = candidate.get("candidate_id", revision["commit"][:12])
    if not isinstance(candidate_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", candidate_id):
        raise DevhubError("Invalid candidate ID.")
    repo_root = Path(git(source, "rev-parse", "--show-toplevel")).resolve()
    source_from_root = source.resolve().relative_to(repo_root)
    parent = (WORK / "worktrees" / profile["id"]).resolve()
    worktree = parent / candidate_id
    if not worktree.resolve().is_relative_to(parent):
        raise DevhubError("WRITE_BLOCKED: candidate worktree escapes its project work area.")
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
            isolated_root = (worktree / source_from_root).resolve()
            if not isolated_root.is_relative_to(worktree.resolve()):
                raise DevhubError("WRITE_BLOCKED: isolated source escapes worktree.")
            target = allowed_path(profile, isolated_root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return worktree
    except Exception:
        subprocess.run(["git", "-C", str(repo_root), "worktree", "remove", "--force", str(worktree)],
                       capture_output=True, check=False)
        raise


def rehydrate(project_id: str, *, initialize_demo: bool = True) -> dict[str, Any]:
    profile, project_dir = project_profile(project_id)
    source = resolve_source(profile, initialize_demo=initialize_demo)
    validate_profile_source(profile, source)
    revision = resolve_revision(profile, source)
    current = load_current(profile, project_dir)
    working = load_current(profile, project_dir, working=True)
    return {"profile": profile, "project_dir": project_dir, "source": source,
            "revision": revision, "current": current, "working": working or current,
            "working_pointer": working["pointer"] if working else None}


def python_graph(source: Path, profile: dict[str, Any], revision: str) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    py_files = sorted(source.rglob("*.py"))
    for path in py_files:
        if path.is_symlink() or not path.resolve().is_relative_to(source.resolve()) or any(
            part in {".git", ".work", "__pycache__"} for part in path.relative_to(source).parts
        ):
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
                    declared_scripts = profile.get("console_entrypoints", {})
                    for command, expected_target in declared_scripts.items():
                        if scripts.get(command) != expected_target:
                            diagnostics.append(
                                f"Console script {command} differs from profile: expected {expected_target}, "
                                f"observed {scripts.get(command, 'MISSING')}."
                            )
                    for command, target in scripts.items():
                        module = target.split(":", 1)[0].replace(".", "/") + ".py"
                        if not (source / module).exists() and (source / "src" / module).exists():
                            module = f"src/{module}"
                        if (source / module).exists():
                            edges.append({"from": build_file, "to": module, "direction": "targets",
                                          "revision": revision, "evidence": "VERIFIZIERT",
                                          "source": build_file})
                            symbol = target.split(":", 1)[1] if ":" in target else ""
                            if symbol:
                                try:
                                    import ast
                                    module_tree = ast.parse((source / module).read_text(encoding="utf-8"))
                                    symbols = {node.name for node in ast.walk(module_tree)
                                               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                                    ast.ClassDef))}
                                    if symbol.split(".", 1)[0] not in symbols:
                                        diagnostics.append(
                                            f"Console script {command} target {target} has no declared symbol."
                                        )
                                except (SyntaxError, UnicodeDecodeError):
                                    diagnostics.append(f"Unable to parse console script module {module}.")
                        else:
                            diagnostics.append(
                                f"Console script {command} target {target} has no tracked Python module."
                            )
                except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                    diagnostics.append(f"Unable to parse build contract {build_file}.")
        for test_path in profile.get("test_paths", []):
            if test_path in profile.get("test_dependencies", {}):
                continue
            nodes.append({"id": test_path, "kind": "test", "source": "project.json",
                          "revision": revision})
            edges.append({"from": entry, "to": test_path, "direction": "validated_by",
                          "revision": revision, "evidence": "ABGELEITET", "source": "project.json"})
            for build_file in profile.get("build_contracts", []):
                edges.append({"from": build_file, "to": test_path, "direction": "checked_by",
                              "revision": revision, "evidence": "ABGELEITET", "source": "project.json"})
    build_contracts = set(profile.get("build_contracts", []))
    for test_path, dependencies in profile.get("test_dependencies", {}).items():
        nodes.append({"id": test_path, "kind": "test", "source": "project.json", "revision": revision})
        for dependency in dependencies:
            edges.append({"from": dependency, "to": test_path,
                          "direction": "checked_by" if dependency in build_contracts else "validated_by",
                          "revision": revision, "evidence": "ABGELEITET", "source": "project.json"})
    return {"revision": revision, "nodes": nodes, "edges": edges, "diagnostics": diagnostics,
            "dynamic_bindings": {"status": "OFFEN", "reason": "Dynamic Python imports are not statically resolved."}}


def plan_entrypoint_repairs(profile: dict[str, Any], source: Path) -> list[dict[str, str]]:
    patches = []
    for build_file in profile.get("build_contracts", []):
        path = source / build_file
        if path.suffix != ".toml" or not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        try:
            scripts = tomllib.loads(original).get("project", {}).get("scripts", {})
        except tomllib.TOMLDecodeError:
            continue
        updated = original
        expected = profile.get("console_entrypoints", {})
        for command, target in expected.items():
            if scripts.get(command) == target:
                continue
            line = re.compile(
                rf"(?m)^([ \t]*){re.escape(command)}([ \t]*=[ \t]*)(['\"])[^'\"\r\n]*\3[ \t]*$"
            )
            updated, count = line.subn(
                lambda match: f'{match.group(1)}{command}{match.group(2)}"{target}"',
                updated, count=1,
            )
            if not count and f"[project.scripts]" in updated:
                updated = re.sub(
                    r"(?m)^(\[project\.scripts\][ \t]*\r?\n)",
                    lambda match: f'{match.group(1)}{command} = "{target}"\n',
                    updated, count=1,
                )
        if updated != original:
            patches.append({"path": build_file, "content": updated})
    return patches


def inspect_project(project_id: str, *, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state if state is not None else rehydrate(project_id, initialize_demo=False)
    current = state["current"]
    working = state["working"]
    last = working["checkpoint"] if working else None
    head = state["revision"]["commit"]
    stale = bool(last and last["observed_head"] != head)
    pending = last["open_work"] if last else []
    next_action = "SYSTEMSTART"
    next_step = "Run SYSTEMSTART to create the first checkpoint"
    if stale:
        next_action, next_step = "WEITER", "Re-audit the new HEAD"
    elif pending:
        next_action = "WEITER" if pending[0].get("status") == "OFFEN" else "CODEFORGE"
        next_step = pending[0].get("step", "Inspect outstanding work")
    elif last:
        next_action, next_step = "STATUS", "Review results and Run UPDATE to publish Current"
    return {
        "id": project_id, "name": state["profile"]["name"], "source_mode": state["profile"]["source_mode"],
        "demo": state["profile"].get("demo", False), "commit": head,
        "current_commit": current["pointer"]["commit"] if current else None,
        "current": current["checkpoint"] if current else None,
        "working_commit": last["observed_head"] if last else None,
        "last_session": last.get("created_at") if last else None,
        "next_step": next_step, "next_action": next_action,
        "revision_status": "PARTIAL" if stale or (current and current["pointer"]["commit"] != head)
                           else "VERIFIZIERT" if last else "OFFEN",
    }


def export_context(project_id: str) -> dict[str, Any]:
    """Return a portable project context without initializing or changing a checkout."""
    profile, _ = project_profile(project_id)
    hub_commit = git(ROOT, "rev-parse", "--verify", "HEAD^{commit}")
    revision = None
    blocker = None
    try:
        source = resolve_source(profile, initialize_demo=False)
        validate_profile_source(profile, source)
        revision = resolve_revision(profile, source)
    except DevhubError:
        blocker = "Verify the project checkout, declared source files, repository identity, and expected ref locally."
    return {
        "schema_version": 1,
        "kind": "666dev-project-context",
        "hub_commit": hub_commit,
        "project_id": project_id,
        "profile_path": project_entries()[project_id],
        "source_mode": profile["source_mode"],
        "source_revision_status": "VERIFIZIERT" if revision else "READBACK_PENDING",
        "source_revision": revision,
        "blocker": blocker,
        "entry_points": profile["entry_points"],
        "build_contracts": profile["build_contracts"],
        "test_paths": profile["test_paths"],
    }


def validate_zip(archive: Path, manifest: dict[str, str]) -> list[str]:
    errors = []
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        entries = set(names)
        if len(entries) != len(names):
            errors.append("ZIP contains duplicate entries.")
        expected = set(manifest)
        if expected | {"manifest.json"} != entries or "manifest.json" in expected:
            errors.append("ZIP entries do not match the manifest.")
        try:
            if json.loads(bundle.read("manifest.json")) != manifest:
                errors.append("Embedded manifest differs from the verified manifest.")
        except (KeyError, ValueError, UnicodeError):
            errors.append("Embedded manifest is missing or unreadable.")
        for name, digest in manifest.items():
            windows_path = PureWindowsPath(name)
            if ("\\" in name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                    or windows_path.is_absolute() or windows_path.drive or ".." in windows_path.parts):
                errors.append(f"Unsafe ZIP entry: {name}")
                continue
            try:
                actual = hashlib.sha256(bundle.read(name)).hexdigest()
                if actual != digest:
                    errors.append(f"Hash mismatch: {name}")
            except KeyError:
                errors.append(f"Missing ZIP entry: {name}")
    return errors


def committed_files(source: Path, revision: str):
    """Yield regular project blobs from an immutable Git tree."""
    from .providers import git_bytes

    root = Path(git(source, "rev-parse", "--show-toplevel")).resolve()
    prefix = source.resolve().relative_to(root).as_posix()
    listing = git_bytes(root, "ls-tree", "-r", "-z", revision, "--", prefix)
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            continue
        name = PurePosixPath(path.decode("utf-8")).relative_to(prefix).as_posix()
        if name == "manifest.json" or "\\" in name or PureWindowsPath(name).drive:
            raise DevhubError("Source contains a path incompatible with the freeze format.")
        yield name, git_bytes(root, "cat-file", "blob", blob), int(mode[-3:], 8)


def run_committed_build(profile: dict[str, Any], source: Path, revision: str) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="666dev-build-") as temporary:
        root = Path(temporary)
        for name, payload, mode in committed_files(source, revision):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            if os.name != "nt":
                path.chmod(mode)
        checks = run_acceptance(profile, root, revision, kind="build", source_kind="committed_copy")
    for item in checks:
        item["environment"] += "; isolated committed source"
    return checks


def freeze_project(profile: dict[str, Any], source: Path, *,
                   revision: str | None = None) -> tuple[Path, dict[str, str]]:
    head = resolve_revision(profile, source)["commit"]
    if revision is not None and revision != head:
        raise DevhubError("CONFLICT_QUARANTINE: source HEAD changed before freeze.")
    revision = head
    directory = WORK / "freezes" / profile["id"]
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(suffix=".zip", prefix=f"{revision[:12]}-", dir=directory)
    os.close(descriptor)
    archive = Path(name)
    manifest: dict[str, str] = {}
    try:
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for relative, payload, mode in committed_files(source, revision):
                manifest[relative] = hashlib.sha256(payload).hexdigest()
                entry = zipfile.ZipInfo(relative)
                entry.create_system = 3
                entry.external_attr = (0o100000 | mode) << 16
                bundle.writestr(entry, payload, compress_type=zipfile.ZIP_DEFLATED)
            if not manifest:
                raise DevhubError("No committed project files found for freeze.")
            bundle.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        failures = validate_zip(archive, manifest)
        if failures:
            raise DevhubError("Freeze ZIP verification failed: " + "; ".join(failures))
    except Exception:
        archive.unlink(missing_ok=True)
        raise
    return archive, manifest


def freeze_start_checks(archive: Path, profile: dict[str, Any], revision: str) -> list[dict[str, Any]]:
    if not profile.get("start_commands"):
        return [make_evidence("start", "project.json", revision, "extracted freeze",
                              "No start command is configured.", "OFFEN")]
    with tempfile.TemporaryDirectory(prefix="666dev-freeze-") as temporary:
        source = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read("manifest.json"))
            if validate_zip(archive, manifest):
                raise DevhubError("Freeze changed before extracted start checks.")
            for entry in bundle.infolist():
                destination = Path(bundle.extract(entry, source))
                if os.name != "nt" and (mode := (entry.external_attr >> 16) & 0o777):
                    destination.chmod(mode)
        evidence = run_acceptance(profile, source, revision, kind="start", source_kind="frozen_bundle")
    for item in evidence:
        item["environment"] += "; extracted freeze"
    return evidence


def dashboard_data() -> dict[str, Any]:
    from .impact import project_impact

    projects = []
    for project_id in sorted(project_entries()):
        try:
            state = rehydrate(project_id, initialize_demo=False)
            profile = state["profile"]
            working = state["working"]["checkpoint"] if state["working"] else None
            item = inspect_project(project_id, state=state)
            current_evidence = list(working["results"]) if working else []
            if state["current"] and state["working_pointer"]:
                current_evidence.extend(record for record in state["current"]["checkpoint"]["results"]
                                        if record.get("evidence_type") == "current-acceptance")
            graph = python_graph(state["source"], profile, item["commit"])
            try:
                impact = project_impact(state, graph=graph)
            except DevhubError as exc:
                impact = {"error": str(exc)}
            projects.append({
                **item,
                "graph": graph,
                "impact": impact,
                "evidence": [record for record in current_evidence if record.get("commit") == item["commit"]],
                "history": sorted(path.name for path in
                                  state_file(state["project_dir"], "checkpoints").glob("*.json")),
                "recovery_anchor": working.get("return_anchor") if working else None,
            })
        except DevhubError as exc:
            projects.append({"id": project_id, "error": str(exc), "evidence": [], "graph": {"nodes": [], "edges": []}})
    return {"generated_at": utc_now(), "projects": projects,
            "providers": {"github": "READBACK_PENDING", "ci": "OFFEN", "target_host": "OFFEN"}}
