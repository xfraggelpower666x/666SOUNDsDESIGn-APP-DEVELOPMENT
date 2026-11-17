from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from pathlib import PureWindowsPath

from .core import (
    ROOT, DevhubError, ID_RE, checkpoint_file, project_entries, project_profile,
    read_json,
)


def verify(base: str | None = None) -> dict:
    errors: list[str] = []
    checked = 0
    changed_files: list[str] = []
    try:
        entries = project_entries()
        for project_id, profile_ref in entries.items():
            checked += 1
            if not ID_RE.fullmatch(project_id):
                errors.append(f"Invalid project ID: {project_id}")
                continue
            try:
                profile, project_dir = project_profile(project_id)
                for key in ("name", "source_mode", "expected_ref", "entry_points",
                            "build_contracts", "writable_paths", "acceptance"):
                    if key not in profile:
                        errors.append(f"{project_id}: missing profile field {key}")
                if profile["source_mode"] not in {"monorepo", "linked"}:
                    errors.append(f"{project_id}: unsupported source_mode")
                if profile["source_mode"] == "monorepo":
                    source = (ROOT / profile["source_path"]).resolve()
                    if not source.is_relative_to(ROOT.resolve()):
                        errors.append(f"{project_id}: source path escapes repository")
                    references = (profile.get("language_files", []) + profile.get("build_contracts", [])
                                  + profile.get("test_paths", []))
                    for relative in references:
                        referenced_path = (source / relative).resolve()
                        if not referenced_path.is_relative_to(source):
                            errors.append(f"{project_id}: reference escapes source {relative}")
                        elif not referenced_path.is_file():
                            errors.append(f"{project_id}: missing referenced file {relative}")
                    for writable in profile.get("writable_paths", []):
                        if PureWindowsPath(writable).is_absolute() or PureWindowsPath(writable).drive:
                            errors.append(f"{project_id}: Windows absolute writable path {writable}")
                        elif not (source / writable).resolve().is_relative_to(source):
                            errors.append(f"{project_id}: writable path escapes source")
                state = project_dir / "state"
                current_path = state / "current.json"
                if current_path.exists():
                    current = read_json(current_path)
                    checkpoint_path = checkpoint_file(project_dir, current["checkpoint_id"])
                    checkpoint = read_json(checkpoint_path)
                    digest = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
                    if current.get("sha256") != digest:
                        errors.append(f"{project_id}: checkpoint hash mismatch")
                    if (checkpoint.get("project_id") != project_id
                            or checkpoint.get("observed_head") != current.get("commit")):
                        errors.append(f"{project_id}: checkpoint project mismatch")
                    if not checkpoint.get("results"):
                        errors.append(f"{project_id}: checkpoint has no evidence")
                    for result in checkpoint.get("results", []):
                        if result.get("status") not in {
                            "VERIFIZIERT", "ABGELEITET", "VORGESCHLAGEN", "OFFEN", "BLOCKIERT",
                            "PARTIAL", "WRITE_BLOCKED", "READBACK_PENDING", "CONFLICT_QUARANTINE",
                        }:
                            errors.append(f"{project_id}: invalid evidence status {result.get('status')}")
                        if not all(result.get(field) for field in
                                   ("evidence_type", "source", "commit", "environment", "observed")):
                            errors.append(f"{project_id}: incomplete evidence record")
            except (DevhubError, KeyError, TypeError) as exc:
                errors.append(f"{project_id}: {exc}")
        if base:
            if base != "HEAD" and subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "--verify", f"{base}^{{commit}}"],
                capture_output=True,
            ).returncode:
                errors.append(f"Diff base cannot be resolved: {base}")
            else:
                diff = subprocess.run(
                    ["git", "-C", str(ROOT), "diff", "--name-only", base],
                    capture_output=True, text=True,
                )
                if diff.returncode:
                    errors.append(f"Scope diff failed for base {base}")
                else:
                    changed = set(diff.stdout.splitlines())
                    untracked = subprocess.run(
                        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard"],
                        capture_output=True, text=True,
                    )
                    if untracked.returncode:
                        errors.append("Untracked-file scope check failed")
                    changed.update(untracked.stdout.splitlines())
                    for name in changed:
                        if name.startswith(".work/"):
                            errors.append(f"Scope diff includes ignored work area: {name}")
                    changed_files = sorted(changed)
        return {
            "status": ("BLOCKIERT" if errors else "VERIFIZIERT" if base else "PARTIAL"),
            "diff_base": base or "UNSPECIFIED (working tree only)",
            "projects_checked": checked,
            "required_sources": {"registry": "VERIFIZIERT", "diff_base": "VERIFIZIERT" if base else "PARTIAL"},
            "changed_files": changed_files,
            "errors": errors,
            "skipped": [] if base else ["Commit-to-HEAD diff comparison: no base supplied"],
        }
    except DevhubError as exc:
        return {"status": "BLOCKIERT", "errors": [str(exc)], "projects_checked": checked}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="666DEV project and state verifier")
    parser.add_argument("--base", help="Commit/ref used for the scope diff")
    args = parser.parse_args(argv)
    result = verify(args.base)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "VERIFIZIERT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
