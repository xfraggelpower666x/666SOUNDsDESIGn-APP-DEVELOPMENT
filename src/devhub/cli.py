from __future__ import annotations

import argparse
import json
import sys
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import (
    ROOT, DevhubError, allowed_path, apply_candidate, checkpoint, dashboard_data, freeze_project, inspect_project,
    git, make_evidence, project_entries, project_profile, python_graph, rehydrate,
    plan_entrypoint_repairs, run_acceptance,
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
                "BLOCKIERT" if graph["diagnostics"] else "VERIFIZIERT",
            ))
        else:
            evidence.append(make_evidence(
                "build-audit", ", ".join(profile.get("build_contracts", [])), commit, "local",
                "; ".join(graph["diagnostics"]) if graph["diagnostics"] else
                "Declared console entry point targets resolve to tracked modules.",
                "BLOCKIERT" if graph["diagnostics"] else "VERIFIZIERT",
            ))
            evidence.append(make_evidence(
                "code-audit", str(state["source"]), commit, "local",
                "Read-only source, build contracts, and acceptance tests analyzed",
                "VERIFIZIERT" if all(item["status"] == "VERIFIZIERT" for item in checks) else "BLOCKIERT",
            ))
        candidate = {
            "schema_version": 1, "project_id": project_id,
            "candidate_id": f"{action.lower()}-{commit[:12]}-{uuid.uuid4().hex[:8]}",
            "base_commit": commit,
            "recovery_anchor": state["current"]["pointer"]["checkpoint_id"] if state["current"] else None,
            "scope": list(profile["writable_paths"]),
            "patches": plan_entrypoint_repairs(profile, state["source"]),
            "status": "VORGESCHLAGEN",
            "findings": [{
                "status": "ABGELEITET",
                "finding": ("; ".join(graph["diagnostics"]) if graph["diagnostics"] else
                            "The declared console entry point resolves to the tracked Python module."),
                "source": profile.get("build_contracts", ["project.json"])[0],
                "related_test": profile.get("test_paths", []),
            }],
        }
        candidate_path = project_dir / "state" / "patch-candidates" / f"{candidate['candidate_id']}.json"
        from .core import atomic_json
        atomic_json(candidate_path, candidate)
        evidence.append(make_evidence(
            "patch-candidate", str(candidate_path.relative_to(ROOT)), commit, "local",
            "Candidate recorded; no application files changed.", "VORGESCHLAGEN",
        ))
        open_work = [{"step": "Review candidate and run acceptance tests",
                      "status": "OFFEN", "depends_on": ["audit"],
                      "candidate": str(candidate_path.relative_to(project_dir))}]
        label = f"{action} audit recorded; candidate is not applied"
    elif action == "WEITER":
        if not open_work or open_work[0].get("status") != "OFFEN":
            raise DevhubError("No valid open step exists; run CODEFORGE or SYSTEMSTART first.")
        next_step = open_work[0]
        if next_step["step"] == "Run CodeForge analysis":
            return _checkpoint_action(project_id, "CODEFORGE")
        if next_step["step"] == "Review candidate and run acceptance tests":
            from .core import read_json
            candidate_path = (project_dir / next_step["candidate"]).resolve() if next_step.get("candidate") else None
            if candidate_path and not candidate_path.is_relative_to(project_dir.resolve()):
                raise DevhubError("WRITE_BLOCKED: candidate reference escapes project state.")
            if candidate_path and candidate_path.is_file():
                candidate = read_json(candidate_path)
            else:
                candidate_paths = sorted((project_dir / "state" / "patch-candidates").glob("*.json"))
                candidates = [read_json(path) for path in candidate_paths]
                candidates = [item for item in candidates
                              if item.get("project_id") == project_id and item.get("base_commit") == commit]
                candidate = candidates[-1] if candidates else {}
            if candidate.get("patches"):
                if candidate_path is None:
                    candidate_path = project_dir / "state" / "patch-candidates" / f"{candidate['candidate_id']}.json"
                raise DevhubError(
                    f"VORGESCHLAGEN: review and explicitly apply {candidate_path.relative_to(project_dir)} first."
                )
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
        if next_step["step"] == "Run re-audit in isolated worktree":
            worktree = Path(next_step["worktree"]).resolve()
            permitted_worktrees = (ROOT / ".work" / "worktrees" / project_id).resolve()
            if not worktree.is_relative_to(permitted_worktrees) or not worktree.is_dir():
                raise DevhubError("WRITE_BLOCKED: isolated worktree is missing or outside its work area.")
            if state["profile"]["source_mode"] == "monorepo":
                source_relative = Path(profile["source_path"])
            else:
                repo_root = Path(git(state["source"], "rev-parse", "--show-toplevel"))
                source_relative = state["source"].relative_to(repo_root)
            isolated_source = (worktree / source_relative).resolve()
            if not isolated_source.is_relative_to(worktree):
                raise DevhubError("WRITE_BLOCKED: isolated project path escapes worktree.")
            checks = run_acceptance(profile, isolated_source, commit)
            graph = python_graph(isolated_source, profile, commit)
            evidence.extend(checks)
            passed = (all(item["status"] == "VERIFIZIERT" for item in checks)
                      and not graph["diagnostics"])
            evidence.append(make_evidence(
                "re-audit", str(worktree), commit, "isolated local Git worktree",
                "Static build audit and acceptance checks passed." if passed else
                "; ".join(graph["diagnostics"]) or "Acceptance checks failed.",
                "VERIFIZIERT" if passed else "BLOCKIERT",
            ))
            open_work = [] if passed else [{"step": "Resolve failed isolated re-audit",
                                            "status": "BLOCKIERT", "depends_on": ["re-audit"]}]
            return checkpoint(profile, project_dir, commit,
                              "Isolated patch re-audit completed" if passed else "Isolated re-audit blocked",
                              evidence, open_work, list(profile["writable_paths"]),
                              next_step.get("affected_files", []))
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
    affected_files = [patch["path"] for patch in candidate.get("patches", [])]
    evidence = list(state["current"]["checkpoint"]["results"]) if state["current"] else []
    evidence.append(make_evidence(
        "patch-apply", candidate_arg, state["revision"]["commit"], "isolated local Git worktree",
        f"Materialized {len(affected_files)} scoped patch(es) at {worktree}.", "VERIFIZIERT",
    ))
    checkpoint(
        state["profile"], state["project_dir"], state["revision"]["commit"],
        "Scoped candidate applied in isolated worktree", evidence,
        [{"step": "Run re-audit in isolated worktree", "status": "OFFEN",
          "depends_on": ["patch-apply"], "worktree": str(worktree),
          "affected_files": affected_files}],
        list(state["profile"]["writable_paths"]), affected_files,
    )
    return f"Scoped patch materialized in isolated worktree: {worktree}; run 666DEV {project_id} WEITER."


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
        if state["current"] and any(
            item.get("status") in {"OFFEN", "BLOCKIERT"}
            for item in state["current"]["checkpoint"].get("open_work", [])
        ):
            raise DevhubError("BLOCKIERT: resolve open or blocked work before UPDATE.")
    elif action not in {"SYSTEMSTART", "WEITER", "CODEFORGE", "SUPERCODEFORGE"}:
        raise DevhubError(f"Unknown action {action}. Try 666DEV HELP.")
    return json.dumps(_checkpoint_action(project_id, action), indent=2)


def main(argv: list[str] | None = None) -> int:
    invoked_as_console_script = Path(sys.argv[0]).name.lower() in {"666dev", "666dev.exe"}
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="*")
    parser.add_argument("--dashboard", action="store_true")
    args = parser.parse_args(argv)
    if args.dashboard or args.command == ["dashboard"]:
        serve_dashboard()
        return 0
    if invoked_as_console_script and args.command and args.command[0].upper() != "666DEV":
        args.command.insert(0, "666DEV")
    try:
        print(execute(args.command))
        return 0
    except DevhubError as exc:
        print(f"666DEV: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
