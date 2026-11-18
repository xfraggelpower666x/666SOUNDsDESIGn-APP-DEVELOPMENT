from __future__ import annotations

import argparse
import json
from pathlib import PureWindowsPath

from .core import (
    ROOT, STATUSES, DevhubError, ID_RE, git, load_current, project_entries, project_profile, rehydrate,
)

from .impact import project_impact
from .providers import git_bytes


def verify(base: str | None = None) -> dict:
    errors: list[str] = []
    checked = 0
    changed_files: list[str] = []
    resolved_base = None
    impacts = []
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
                for working in (False, True):
                    state = load_current(profile, project_dir, working=working)
                    if state is None:
                        continue
                    for result in state["checkpoint"]["results"]:
                        if not isinstance(result, dict) or result.get("status") not in STATUSES:
                            errors.append(f"{project_id}: invalid evidence status")
                        elif not all(result.get(field) for field in
                                     ("evidence_type", "source", "commit", "environment", "observed")):
                            errors.append(f"{project_id}: incomplete evidence record")
                manifest = project_dir / "development-manifest.json"
                if manifest.exists():
                    from .manifests import inspect_manifest
                    if not manifest.resolve().is_relative_to(project_dir):
                        raise DevhubError("Manifest path escapes the project directory.")
                    inspect_manifest(project_id, manifest)
            except (DevhubError, KeyError, TypeError) as exc:
                errors.append(f"{project_id}: {exc}")
        if base:
            try:
                resolved_base = git(ROOT, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}")
                inventories = (
                    git_bytes(ROOT, "diff", "--name-only", "-z", resolved_base, "--"),
                    git_bytes(ROOT, "diff", "--cached", "--name-only", "-z", "--"),
                    git_bytes(ROOT, "diff", "--name-only", "-z", "--"),
                    git_bytes(ROOT, "ls-files", "--others", "--exclude-standard", "-z"),
                )
                changed_files = sorted({name.decode("utf-8", errors="surrogateescape")
                                        for inventory in inventories for name in inventory.split(b"\0") if name})
                for name in changed_files:
                    if name.startswith(".work/"):
                        errors.append(f"Scope diff includes ignored work area: {name}")
            except DevhubError as exc:
                errors.append(f"Diff base or scope could not be verified: {exc}")
        for project_id in entries:
            try:
                state = rehydrate(project_id, initialize_demo=False)
                project_base = resolved_base if state["profile"]["source_mode"] == "monorepo" else None
                impacts.append(project_impact(state, base=project_base))
            except DevhubError as exc:
                impacts.append({"project_id": project_id, "error": str(exc), "checks": []})
        return {
            "status": ("BLOCKIERT" if errors else "VERIFIZIERT" if base else "PARTIAL"),
            "diff_base": resolved_base or base or "UNSPECIFIED (working tree only)",
            "projects_checked": checked,
            "required_sources": {"registry": "VERIFIZIERT", "diff_base": "VERIFIZIERT" if resolved_base else "PARTIAL"},
            "changed_files": changed_files,
            "project_impacts": impacts,
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
