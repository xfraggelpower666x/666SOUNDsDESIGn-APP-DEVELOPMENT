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
    if not isinstance(profile.get("expected_ref"), str) or not profile["expected_ref"]:
        raise DevhubError(f"Profile {project_id} requires expected_ref.")
    for key in ("build_commands", "test_commands"):
        commands = profile.get(key, [])
        if not isinstance(commands, list) or any(not isinstance(command, str) or not command.strip()
                                                 for command in commands):
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
    if (current.get("schema_version") != 1 or current.get("project_id") != profile["id"]
            or current.get("sha256") != digest or body.get("project_id") != profile["id"]
            or body.get("schema_version") != 1 or body.get("checkpoint_id") != current["checkpoint_id"]
            or current.get("commit") != body.get("observed_head")):
        raise DevhubError("Current/checkpoint integrity mismatch; quarantined for recovery.")
    return {"pointer": current, "checkpoint": body}


def checkpoint(profile: dict[str, Any], project_dir: Path, revision: str, task: str,
               evidence: list[dict[str, Any]], open_work: list[dict[str, Any]], scope: list[str],
               affected_files: list[str] | None = None) -> dict[str, Any]:
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
            "affected_files": affected_files or [], "results": evidence, "open_work": open_work,
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
    commands = profile.get("test_commands", [])
    for configured in commands:
        command = shlex.split(configured, posix=os.name != "nt")
        if not command:
            evidence.append(make_evidence("test", configured, revision,
                                          f"{sys.platform}; Python {sys.version.split()[0]}",
                                          "Configured acceptance command is empty.", "BLOCKIERT"))
            continue
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
    if not commands:
        evidence.append(make_evidence("test", "project.json", revision,
                                      f"{sys.platform}; Python {sys.version.split()[0]}",
                                      "No acceptance test command is configured.", "BLOCKIERT"))
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
    validate_profile_source(profile, source)
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
    diagnostics: list[str] = []
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
            nodes.append({"id": test_path, "kind": "test", "source": "project.json",
                          "revision": revision})
            edges.append({"from": entry, "to": test_path, "direction": "validated_by",
                          "revision": revision, "evidence": "ABGELEITET", "source": "project.json"})
            for build_file in profile.get("build_contracts", []):
                edges.append({"from": build_file, "to": test_path, "direction": "checked_by",
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
        if expected != entries - {"manifest.json"}:
            errors.append("ZIP entries do not match the manifest.")
        for name, digest in manifest.items():
            windows_path = PureWindowsPath(name)
            if (PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
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
