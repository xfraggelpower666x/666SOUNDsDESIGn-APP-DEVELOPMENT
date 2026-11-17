from __future__ import annotations

import argparse
import json
import shlex
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .core import (
    ROOT, DevhubError, allowed_path, apply_candidate, checkpoint, dashboard_data, freeze_project, inspect_project,
    make_evidence, project_entries, project_profile, python_graph, rehydrate,
    run_acceptance,
)

HELP = """666DEV commands (parsed only from this direct invocation):
  666DEV HELP
  666DEV STATUS
  666DEV <PROJECT-ID> SYSTEMSTART|STATUS|WEITER|CODEFORGE|SUPERCODEFORGE|VISUAL|UPDATE|FREEZE
  666DEV <PROJECT-ID> PATCH-APPLY <candidate.json>

Examples:
  python -m devhub.cli 666DEV demo-monorepo SYSTEMSTART
  python -m devhub.cli 666DEV demo-linked STATUS
"""


def _checkpoint_action(project_id: str, action: str) -> dict:
    state = rehydrate(project_id)
    profile, project_dir = state["profile"], state["project_dir"]
    commit = state["revision"]["commit"]
    evidence = list(state["current"]["checkpoint"]["results"]) if state["current"] else []
    open_work = list(state["current"]["checkpoint"]["open_work"]) if state["current"] else []
    if action == "SYSTEMSTART":
        evidence.append(make_evidence("git", str(state["source"]), commit, "local",
                                      f"Ref {state['revision']['expected_ref']} resolved to HEAD"))
        open_work = [{"step": "Run CodeForge analysis", "status": "OFFEN", "depends_on": []}]
        label = "Rehydration and project source verified"
    elif action in {"CODEFORGE", "SUPERCODEFORGE"}:
        graph = python_graph(state["source"], profile, commit)
        checks = run_acceptance(profile, state["source"], commit) if action == "CODEFORGE" else []
        evidence.extend(checks)
        if action == "SUPERCODEFORGE":
            evidence.append(make_evidence(
                "static-graph", "project.json, Python AST", commit, "local",
                f"{len(graph['nodes'])} nodes; {len(graph['edges'])} edges; dynamic bindings remain open",
            ))
        else:
            evidence.append(make_evidence(
                "code-audit", str(state["source"]), commit, "local",
                "Read-only source, build contracts, and acceptance tests analyzed",
                "VERIFIZIERT" if all(item["status"] == "VERIFIZIERT" for item in checks) else "BLOCKIERT",
            ))
        candidate = {
            "schema_version": 1, "project_id": project_id, "candidate_id": f"{action.lower()}-{commit[:12]}",
            "base_commit": commit,
            "recovery_anchor": state["current"]["pointer"]["checkpoint_id"] if state["current"] else None,
            "scope": list(profile["writable_paths"]), "patches": [], "status": "VORGESCHLAGEN",
            "findings": [{
                "status": "ABGELEITET",
                "finding": "The declared console entry point resolves to the tracked Python module.",
                "source": profile.get("build_contracts", ["project.json"])[0],
                "related_test": profile.get("test_paths", []),
            }],
        }
        candidate_path = project_dir / "state" / "patch-candidates" / f"{action.lower()}-{commit[:12]}.json"
        from .core import atomic_json
        atomic_json(candidate_path, candidate)
        evidence.append(make_evidence(
            "patch-candidate", str(candidate_path.relative_to(ROOT)), commit, "local",
            "Candidate recorded; no application files changed.", "VORGESCHLAGEN",
        ))
        open_work = [{"step": "Review candidate and run acceptance tests",
                      "status": "OFFEN", "depends_on": ["audit"]}]
        label = f"{action} audit recorded; candidate is not applied"
    elif action == "WEITER":
        if not open_work or open_work[0].get("status") != "OFFEN":
            raise DevhubError("No valid open step exists; run CODEFORGE or SYSTEMSTART first.")
        next_step = open_work[0]
        if next_step["step"] == "Run CodeForge analysis":
            return _checkpoint_action(project_id, "CODEFORGE")
        if next_step["step"] == "Review candidate and run acceptance tests":
            checks = run_acceptance(profile, state["source"], commit)
            evidence.extend(checks)
            passed = all(item["status"] == "VERIFIZIERT" for item in checks)
            open_work = [] if passed else [{"step": "Resolve failed acceptance checks",
                                            "status": "BLOCKIERT", "depends_on": ["tests"]}]
            evidence.append(make_evidence(
                "re-audit", "666DEV WEITER", commit, "local",
                "Acceptance checks passed." if passed else "Acceptance checks failed; inspect preceding test evidence.",
                "VERIFIZIERT" if passed else "BLOCKIERT",
            ))
            label = "Re-audit completed" if passed else "Re-audit blocked"
            return checkpoint(profile, project_dir, commit, label, evidence, open_work,
                              list(profile["writable_paths"]))
        evidence.append(make_evidence(
            "workflow-step", next_step["step"], commit, "local",
            "Resolved as an explicit read-only next action.", "ABGELEITET",
        ))
        label = f"Resolved next action: {next_step['step']}"
    elif action == "UPDATE":
        evidence.append(make_evidence(
            "current-update", "666DEV UPDATE", commit, "local",
            "Git HEAD and project scope verified; pointer updated last.",
        ))
        label = "Explicit Current update"
    else:
        raise DevhubError(f"Unsupported action: {action}")
    return checkpoint(profile, project_dir, commit, label, evidence, open_work,
                      list(profile["writable_paths"]))


def render_status(project_id: str | None = None) -> str:
    ids = [project_id] if project_id else sorted(project_entries())
    return "\n".join(
        f"{item['id']}: {item['name']} | {item['source_mode']} | {item['revision_status']} | "
        f"{item['commit'][:12]} | next: {item['next_step']}"
        for item in (inspect_project(selected) for selected in ids)
    )


def serve_dashboard() -> None:
    from .core import atomic_json
    dashboard = ROOT / "web"
    atomic_json(dashboard / "dashboard.json", dashboard_data())

    class LocalOnlyHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dashboard), **kwargs)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 8766), LocalOnlyHandler)
    print("Read-only dashboard: http://127.0.0.1:8766")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _patch_apply(project_id: str, candidate_arg: str) -> str:
    state = rehydrate(project_id)
    candidate_path = (state["project_dir"] / candidate_arg).resolve()
    if not candidate_path.is_relative_to(state["project_dir"].resolve()):
        raise DevhubError("WRITE_BLOCKED: candidate path escapes the selected project.")
    from .core import read_json
    candidate = read_json(candidate_path)
    if candidate.get("project_id") != project_id or candidate.get("base_commit") != state["revision"]["commit"]:
        raise DevhubError("Candidate project or base revision mismatch.")
    if candidate.get("status") != "VORGESCHLAGEN":
        raise DevhubError("Candidate is not in proposed state.")
    for path in candidate.get("scope", []):
        allowed_path(state["profile"], state["source"], path)
    worktree = apply_candidate(state["profile"], state["source"], candidate)
    return f"Scoped patch materialized in isolated worktree: {worktree}"


def execute(tokens: list[str]) -> str:
    normalized = list(tokens)
    if normalized:
        normalized[0] = normalized[0].upper()
    if len(normalized) > 1:
        normalized[1] = normalized[1].upper()
    if len(normalized) > 2:
        normalized[2] = normalized[2].upper()
    if not normalized or normalized[0] != "666DEV":
        raise DevhubError("A namespace-qualified 666DEV command is required. Try 666DEV HELP.")
    if len(normalized) == 1 or normalized[1] == "HELP":
        return HELP
    if normalized[1] == "STATUS":
        if len(normalized) != 2:
            raise DevhubError("Global STATUS takes no project argument.")
        return render_status()
    if len(normalized) < 3:
        raise DevhubError("Project selection is required.")
    project_id, action = normalized[1].lower(), normalized[2]
    project_profile(project_id)
    if action == "STATUS":
        return render_status(project_id)
    if action == "VISUAL":
        return "Run: python -m devhub.cli dashboard"
    if action == "FREEZE":
        state = rehydrate(project_id)
        archive, manifest = freeze_project(state["profile"], state["source"])
        return json.dumps({"status": "VERIFIZIERT", "archive": str(archive),
                           "files": len(manifest), "manifest_sha256": {
                               name: digest for name, digest in manifest.items()
                           }}, indent=2)
    if action == "PATCH-APPLY":
        if len(normalized) != 4:
            raise DevhubError("PATCH-APPLY requires a candidate path.")
        return _patch_apply(project_id, normalized[3])
    if action == "UPDATE":
        state = rehydrate(project_id)
        if state["current"] and state["current"]["checkpoint"]["observed_head"] != state["revision"]["commit"]:
            raise DevhubError("CONFLICT_QUARANTINE: HEAD differs from Current; re-audit before UPDATE.")
    elif action not in {"SYSTEMSTART", "WEITER", "CODEFORGE", "SUPERCODEFORGE"}:
        raise DevhubError(f"Unknown action {action}. Try 666DEV HELP.")
    return json.dumps(_checkpoint_action(project_id, action), indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="*")
    parser.add_argument("--dashboard", action="store_true")
    args = parser.parse_args(argv)
    if args.dashboard or args.command == ["dashboard"]:
        serve_dashboard()
        return 0
    try:
        print(execute(shlex.split(" ".join(args.command))))
        return 0
    except DevhubError as exc:
        print(f"666DEV: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
