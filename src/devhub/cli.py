from __future__ import annotations

import argparse
import json
import sys
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import (
    ROOT, DevhubError, allowed_path, apply_candidate, checkpoint, clean_source, dashboard_data, export_context, freeze_project, freeze_start_checks, inspect_project,
    git, make_evidence, project_entries, project_profile, python_graph, rehydrate,
    plan_entrypoint_repairs, run_acceptance, run_committed_build, state_file, unresolved_conflicts,
)

HELP = """666DEV commands (parsed only from this direct invocation):
  666DEV HELP
  666DEV STATUS
  666DEV SYSTEMSTART | UPDATE | FUCK HORST
  666DEV DESKTOP-IMPACT [BASE]
  666DEV COST-POLICY | COST-CHECK <EVENT> <COST-CLASS> (read-only)
  666DEV CODEFORGE-TEAM STATUS | PLAN <proposal.json> (read-only)
  666DEV CODEFORGE-TEAM PEER-READBACK <peer-request.json> (public GitHub GET only)\n  666DEV CODEFORGE-TEAM EXECUTE <proposal.json> <stream-id> <candidate-relative> <sha256> (isolated local only)
  666DEV CODEFORGE-TEAM DRAFT-PR <project-id> <receipt-id> <base-commit> <target-branch> CONFIRM_DRAFT_PR
  666DEV CLIC-HANDOFF INSPECT <handoff.json> (read-only; GitHub readback separate)
  666DEV REPO-MIND CHECK [RENAME-BASE] | INDEX | PR <RENAME-BASE> <TARGET-BRANCH>
  666DEV <PROJECT-ID> FUCK HORST [handoff.json]
  666DEV <PROJECT-ID> SYSTEMSTART|STATUS|WEITER|CODEFORGE|SUPERCODEFORGE|VISUAL|UPDATE|FREEZE
  666DEV <PROJECT-ID> CONTEXT|BUILD
  666DEV <PROJECT-ID> LIVECIRCLE|REHYDRATE|NEW-CHAT
  666DEV <PROJECT-ID> NEXT-CHAT <handoff.json>
  666DEV <PROJECT-ID> IMPACT [BASE]
  666DEV <PROJECT-ID> CAUSAL [BASE] (read-only R03 plan)
  666DEV <PROJECT-ID> CODING-PROFI SYSTEMSTART|STATUS|LIVECIRCLE|WEITER|NEW-CHAT
  666DEV <PROJECT-ID> CODING-PROFI NEXT-CHAT <handoff.json> (read-only)
  666DEV <PROJECT-ID> MANIFEST [manifest.json|cards.zip]
  666DEV <PROJECT-ID> PATCH-APPLY <candidate.json>
  666DEV <PROJECT-ID> FACET-STATUS <facet-id>
  666DEV <PROJECT-ID> FACET-SAVE <facet-id> <checkpoint-input.json>

Examples:
  python -m devhub.cli 666DEV demo-monorepo SYSTEMSTART
  python -m devhub.cli 666DEV demo-linked STATUS
"""


def _checkpoint_action(project_id: str, action: str) -> dict:
    state = rehydrate(project_id)
    profile, project_dir = state["profile"], state["project_dir"]
    commit = state["revision"]["commit"]
    if action in {"WEITER", "UPDATE"} and unresolved_conflicts(state["source"]):
        raise DevhubError("CONFLICT_QUARANTINE: resolve the project Git index conflicts before continuing.")
    previous = state["working"]["checkpoint"] if state["working"] else None
    stale = previous is not None and previous["observed_head"] != commit
    evidence = [item for item in previous["results"] if item.get("commit") == commit] if previous else []
    open_work = list(previous["open_work"]) if previous and not stale else []
    if stale:
        evidence.append(make_evidence("revision-change", "Git HEAD", commit, "local",
                                      "Earlier evidence is retained in the previous checkpoint; re-audit required.",
                                      "ABGELEITET"))
        if action == "WEITER":
            action = "CODEFORGE"
    if action == "SYSTEMSTART":
        evidence.append(make_evidence("git", str(state["source"]), commit, "local",
                                      f"Ref {state['revision']['expected_ref']} resolved to HEAD"))
        if previous is None or stale:
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
            "recovery_anchor": state["working"]["pointer"]["checkpoint_id"] if state["working"] else None,
            "scope": list(profile["writable_paths"]),
            "patches": plan_entrypoint_repairs(profile, state["source"]),
            "status": "VORGESCHLAGEN",
            "findings": [{
                "status": "ABGELEITET",
                "finding": ("; ".join(graph["diagnostics"]) if graph["diagnostics"] else
                            "The declared console entry point resolves to the tracked Python module."),
                "source": (profile.get("build_contracts") or ["project.json"])[0],
                "related_test": profile.get("test_paths", []),
            }],
        }
        candidate_path = state_file(project_dir, "patch-candidates", f"{candidate['candidate_id']}.json")
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
            if not candidate_path or not candidate_path.is_relative_to(state_file(project_dir, "patch-candidates")):
                raise DevhubError("WRITE_BLOCKED: checkpoint does not reference a project candidate.")
            candidate = read_json(candidate_path)
            if (candidate.get("project_id") != project_id or candidate.get("base_commit") != commit):
                raise DevhubError("CONFLICT_QUARANTINE: candidate no longer matches the project and HEAD.")
            if candidate.get("patches"):
                raise DevhubError(
                    f"VORGESCHLAGEN: review and explicitly apply {candidate_path.relative_to(project_dir)} first."
                )
            checks = run_acceptance(profile, state["source"], commit)
            evidence.extend(checks)
            diagnostics = python_graph(state["source"], profile, commit)["diagnostics"]
            passed = all(item["status"] == "VERIFIZIERT" for item in checks) and not diagnostics
            open_work = [] if passed else [{"step": "Resolve failed acceptance checks",
                                            "status": "BLOCKIERT", "depends_on": ["tests"]}]
            evidence.append(make_evidence(
                "re-audit", "666DEV WEITER", commit, "local",
                "Acceptance checks passed." if passed else "; ".join(diagnostics) or "Acceptance checks failed.",
                "VERIFIZIERT" if passed else "BLOCKIERT",
            ))
            label = "Re-audit completed" if passed else "Re-audit blocked"
            return checkpoint(profile, project_dir, commit, label, evidence, open_work,
                              list(profile["writable_paths"]), observed=state)
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
            checks = run_acceptance(profile, isolated_source, commit, source_kind="isolated_candidate")
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
                              next_step.get("affected_files", []), observed=state)
        raise DevhubError("Unknown checkpoint step; run CODEFORGE to create a new audit.")
    elif action == "BUILD":
        evidence.extend(run_committed_build(profile, state["source"], commit))
        label = "Build commands executed; inspect build evidence"
    elif action == "UPDATE":
        if previous is None or stale or open_work:
            raise DevhubError("BLOCKIERT: complete the audit and re-audit at the current HEAD before UPDATE.")
        if previous.get("affected_files"):
            raise DevhubError("BLOCKIERT: integrate the isolated candidate into the source revision and re-audit it before UPDATE.")
        if not clean_source(state["source"]):
            raise DevhubError("WRITE_BLOCKED: commit or isolate source changes before publishing Current.")
        checks = run_acceptance(profile, state["source"], commit)
        if profile.get("build_commands"):
            checks.extend(run_committed_build(profile, state["source"], commit))
        diagnostics = python_graph(state["source"], profile, commit)["diagnostics"]
        if diagnostics or any(item["status"] != "VERIFIZIERT" for item in checks):
            raise DevhubError("BLOCKIERT: current checkout failed acceptance; run CODEFORGE for details.")
        evidence.extend(checks)
        evidence.append(make_evidence(
            "current-acceptance", "666DEV UPDATE", commit, "local",
            "Source checkout passed fresh tests, configured builds, and static build-contract checks.",
        ))
        label = "Explicit Current update"
    else:
        raise DevhubError(f"Unsupported action: {action}")
    return checkpoint(profile, project_dir, commit, label, evidence, open_work,
                      list(profile["writable_paths"]), observed=state, publish=action == "UPDATE")


def render_status(project_id: str | None = None) -> str:
    ids = [project_id] if project_id else sorted(project_entries())
    lines = []
    for selected in ids:
        try:
            item = inspect_project(selected)
        except DevhubError as exc:
            lines.append(f"{selected}: OFFEN | {exc}")
            continue
        lines.append(f"{item['id']}: {item['name']} | {item['source_mode']} | {item['revision_status']} | "
                     f"HEAD {item['commit'][:12]} | Current {(item['current_commit'] or 'OFFEN')[:12]} | "
                     f"next: {item['next_step']}")
        if project_id:
            report = snapshot(selected)
            for kind, lane in report.get("acceptance", {}).items():
                for issue in lane["issues"]:
                    exit_code = issue["exit_code"]
                    detail = f"Exitcode {exit_code}" if exit_code is not None else issue["state"]
                    lines.append(f"  {kind}_commands[{issue['command_index'] - 1}]: {detail}")
    return "\n".join(lines)


def serve_dashboard() -> None:
    from urllib.parse import urlsplit

    class LocalOnlyHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

        def do_GET(self):
            if self.headers.get("Host") not in {"127.0.0.1:8766", "localhost:8766"}:
                self.send_error(403)
                return
            path = urlsplit(self.path).path
            if path in {"/", "/index.html", "/app.js", "/style.css"}:
                super().do_GET()
            elif path == "/dashboard.json":
                try:
                    payload = json.dumps(dashboard_data()).encode("utf-8")
                except DevhubError:
                    self.send_error(503, "Project data unavailable")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_error(404)

        def do_HEAD(self):
            self.send_error(405)

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
    if unresolved_conflicts(state["source"]):
        raise DevhubError("CONFLICT_QUARANTINE: resolve the project Git index conflicts before applying a patch.")
    candidate_path = (state["project_dir"] / candidate_arg).resolve()
    if not candidate_path.is_relative_to(state_file(state["project_dir"], "patch-candidates")):
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
    evidence = [item for item in state["working"]["checkpoint"]["results"]
                if item.get("commit") == state["revision"]["commit"]] if state["working"] else []
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
        list(state["profile"]["writable_paths"]), affected_files, observed=state,
    )
    return f"Scoped patch materialized in isolated worktree: {worktree}; run 666DEV {project_id} WEITER."


def _read_handoff(path: str) -> dict:
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            raise ValueError("handoff exceeds 8192 bytes")
        handoff = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(handoff, dict):
            raise ValueError("handoff must be a JSON object")
        return handoff
    except (OSError, ValueError) as exc:
        raise DevhubError("Cannot read the 666DEV handoff.") from exc


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
    if normalized[1] in {"COST-POLICY", "COST-CHECK"}:
        from .intelligence.cost_guard import evaluate, policy_snapshot
        if normalized[1] == "COST-POLICY":
            if len(normalized) != 2:
                raise DevhubError("COST-POLICY takes no arguments.")
            return json.dumps(policy_snapshot(), indent=2, ensure_ascii=False)
        if len(normalized) != 4:
            raise DevhubError("COST-CHECK needs an event and cost class.")
        try:
            return json.dumps(evaluate(normalized[2], normalized[3]),
                              indent=2, ensure_ascii=False)
        except ValueError as exc:
            raise DevhubError(str(exc)) from exc
    if normalized[1] == "CODEFORGE-TEAM":
        from .intelligence.codeforge_cooperation import catalog, plan
        if len(normalized) == 3 and normalized[2] == "STATUS":
            return json.dumps(catalog(), indent=2, ensure_ascii=False)
        if len(normalized) == 4 and normalized[2] == "PLAN":
            proposal = _read_handoff(tokens[3])
            # Reuse the native project LiveCircle, not a peer-provided authority.
            if not isinstance(proposal, dict) or not isinstance(proposal.get("project_id"), str):
                raise DevhubError("CODEFORGE-TEAM requires a project-bound proposal.")
            from .livecircle import snapshot
            project_profile(proposal["project_id"])
            native = snapshot(proposal["project_id"])
            return json.dumps(plan(proposal, native=native), indent=2, ensure_ascii=False)
        if len(normalized) == 7 and normalized[2] == "EXECUTE":
            from .intelligence.codeforge_execution import execute_native
            proposal = _read_handoff(tokens[3])
            if not isinstance(proposal.get("project_id"), str):
                raise DevhubError("Executable CodeForge requires a native project identity.")
            project_profile(proposal["project_id"])
            from .livecircle import snapshot
            native = snapshot(proposal["project_id"])
            return json.dumps(execute_native(
                proposal, workstream_id=tokens[4],
                candidate_relative=tokens[5],
                expected_candidate_sha256=tokens[6], native=native,
            ), indent=2, ensure_ascii=False)
        if len(normalized) == 4 and normalized[2] == "PEER-READBACK":
            from .intelligence.codeforge_peer_readback import inspect
            return json.dumps(inspect(_read_handoff(tokens[3])),
                              indent=2, ensure_ascii=False)
        if len(normalized) == 8 and normalized[2] == "DRAFT-PR":
            from .intelligence.codeforge_publication import publish_draft
            return json.dumps(publish_draft(
                project_id=tokens[3], receipt_id=tokens[4],
                expected_head=tokens[5], target_branch=tokens[6],
                confirmation=tokens[7],
            ), indent=2, ensure_ascii=False)
        raise DevhubError("Use 666DEV CODEFORGE-TEAM STATUS, PLAN <proposal.json> or EXECUTE <proposal.json> <stream-id> <candidate-relative> <sha256>.")
    if normalized[1] == "CLIC-HANDOFF":
        from .intelligence.clic_handoff import inspect
        if len(normalized) != 4 or normalized[2] != "INSPECT":
            raise DevhubError("CLIC-HANDOFF expects INSPECT and one JSON file.")
        # A local file cannot prove live GitHub publication or blob by itself.
        # Never accept caller-provided SHA strings here as remote proof.
        data = _read_handoff(tokens[3])
        return json.dumps(inspect(data), indent=2, ensure_ascii=False)
    if normalized[1] == "DESKTOP-IMPACT":
        from .desktop_impact import desktop_impact

        if len(tokens) > 3:
            raise DevhubError("DESKTOP-IMPACT erwartet höchstens eine Git-Prüfbasis.")
        head = git(ROOT, "rev-parse", "--verify", "HEAD^{commit}")
        return json.dumps(desktop_impact(ROOT, head, tokens[2] if len(tokens) == 3 else None),
                          indent=2, ensure_ascii=False)
    if normalized[1] == "REPO-MIND":
        from .repo_mind import publish, refresh_index, scan

        args = tokens[3:]
        action = normalized[2] if len(normalized) > 2 else "CHECK"
        if action == "CHECK" and len(args) <= 1:
            report, _ = scan(ROOT, *args)
        elif action == "INDEX" and not args:
            report = refresh_index(ROOT)
        elif action == "PR" and len(args) == 2:
            report = publish(ROOT, *args)
        else:
            raise DevhubError("Use 666DEV REPO-MIND CHECK [BASE], INDEX or PR <BASE> <TARGET-BRANCH>.")
        return json.dumps(report, indent=2, ensure_ascii=False)
    if normalized[1] == "STATUS":
        if len(normalized) != 2:
            raise DevhubError("Global STATUS takes no project argument.")
        return render_status()
    from .livecircle import ACTIONS as LIVECIRCLE_ACTIONS, diagnose, hub_entry, resume, snapshot

    if normalized[1:] == ["SYSTEMSTART"]:
        return json.dumps(hub_entry(), indent=2, ensure_ascii=False)
    if normalized[1:] == ["UPDATE"]:
        return json.dumps(hub_entry(update=True), indent=2, ensure_ascii=False)
    if normalized[1:] == ["FUCK", "HORST"]:
        return json.dumps(diagnose(), indent=2, ensure_ascii=False)
    if len(normalized) < 3:
        raise DevhubError("Project selection is required.")
    project_id, action = normalized[1].lower(), normalized[2]
    project_profile(project_id)
    if action == "FUCK" and len(normalized) in (4, 5) and normalized[3].upper() == "HORST":
        handoff = _read_handoff(normalized[4]) if len(normalized) == 5 else None
        return json.dumps(diagnose(project_id, handoff), indent=2, ensure_ascii=False)
    if action not in {"PATCH-APPLY", "MANIFEST", "IMPACT", "CAUSAL", "NEXT-CHAT", "FACET-STATUS", "FACET-SAVE", "CODING-PROFI"} and len(normalized) != 3:
        raise DevhubError(f"{action} takes only a project ID.")
    if action == "STATUS":
        return render_status(project_id)
    if action in LIVECIRCLE_ACTIONS:
        if action == "NEXT-CHAT":
            if len(normalized) != 4:
                raise DevhubError("NEXT-CHAT requires one handoff path.")
            return json.dumps(resume(project_id, _read_handoff(normalized[3])), indent=2, ensure_ascii=False)
        return json.dumps(snapshot(project_id), indent=2, ensure_ascii=False)
    if action in {"FACET-STATUS", "FACET-SAVE"}:
        from .intelligence.facet_store import read_checkpoint, save_checkpoint
        if len(normalized) != (4 if action == "FACET-STATUS" else 5):
            raise DevhubError("FACET-STATUS requires a facet; FACET-SAVE requires facet and JSON input.")
        facet = normalized[3].lower()
        native = snapshot(project_id)
        if action == "FACET-STATUS":
            return json.dumps(read_checkpoint(project_id, facet, native), indent=2, ensure_ascii=False)
        # Only direct CLI invocation grants this local facet-write route.
        source = Path(normalized[4])
        if not source.is_file() or source.is_symlink() or source.stat().st_size > 8192:
            raise DevhubError("Facet input must be a regular JSON file <= 8 KB.")
        try:
            payload = json.loads(source.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise DevhubError("Invalid facet input JSON.") from exc
        if not isinstance(payload, dict) or set(payload) != {
                "state", "last_verified_step", "obligations", "evidence_ids",
                "return_anchor", "expected_digest"}:
            raise DevhubError("Facet input schema mismatch.")
        report = save_checkpoint(project_id, facet, native, **payload)
        return json.dumps(report, indent=2, ensure_ascii=False)
    if action == "CODING-PROFI":
        from .intelligence.coding_profi import trigger, ACTIONS
        from .intelligence.facet_store import read_checkpoint
        if len(normalized) not in (4, 5):
            raise DevhubError("CODING-PROFI expects a native facet action and optional handoff.")
        verb = normalized[3]
        if verb not in ACTIONS or (verb == "NEXT-CHAT") != (len(normalized) == 5):
            raise DevhubError("Invalid CODING-PROFI facet action or handoff arguments.")
        native = snapshot(project_id)
        saved = read_checkpoint(project_id, "coding-profi", native)
        handoff = _read_handoff(normalized[4]) if verb == "NEXT-CHAT" else None
        return json.dumps(trigger(verb, native, project_id=project_id,
                                  saved=saved, handoff=handoff), indent=2, ensure_ascii=False)
    if action == "CAUSAL":
        from .impact import project_impact
        from .intelligence.causal_learning import plan_revalidation
        if len(normalized) > 4:
            raise DevhubError("CAUSAL accepts only one optional Git base.")
        from .livecircle import snapshot
        observed = snapshot(project_id)
        if observed["status"] in {"READBACK_PENDING", "CONFLICT_QUARANTINE", "BLOCKIERT", "WRITE_BLOCKED"}:
            return json.dumps({"status": "READBACK_PENDING", "reason": "Native project cannot be safely analyzed.",
                               "project_id": project_id, "source_revision": observed.get("source_commit"),
                               "recheck_all": True, "checks": []}, indent=2, ensure_ascii=False)
        state = rehydrate(project_id, initialize_demo=False)
        base = normalized[3] if len(normalized) == 4 else None
        impact = project_impact(state, base=base)
        return json.dumps(plan_revalidation(impact, project_id=project_id,
                          revision=state["revision"]["commit"]), indent=2, ensure_ascii=False)
    if action == "IMPACT":
        from .impact import project_impact

        if len(normalized) > 4:
            raise DevhubError("IMPACT accepts only one optional Git base.")
        state = rehydrate(project_id, initialize_demo=False)
        base = normalized[3] if len(normalized) == 4 else None
        return json.dumps(project_impact(state, base=base), indent=2)
    if action == "MANIFEST":
        from .manifests import inspect_manifest

        if len(normalized) > 4:
            raise DevhubError("MANIFEST accepts only one optional input file.")
        _, project_dir = project_profile(project_id)
        path = Path(normalized[3]) if len(normalized) == 4 else project_dir / "development-manifest.json"
        return json.dumps(inspect_manifest(project_id, path), indent=2, ensure_ascii=False)
    if action == "CONTEXT":
        return json.dumps(export_context(project_id), indent=2)
    if action == "VISUAL":
        return f"Run: python -m devhub.cli dashboard\nOpen: http://127.0.0.1:8766/?project={project_id}"
    if action == "FREEZE":
        state = rehydrate(project_id)
        revision = state["revision"]["commit"]
        archive, manifest = freeze_project(state["profile"], state["source"], revision=revision)
        checks = freeze_start_checks(archive, state["profile"], revision)
        from hashlib import file_digest
        with archive.open("rb") as stream:
            digest = file_digest(stream, "sha256").hexdigest()
        start_status = "VERIFIZIERT" if all(item["status"] == "VERIFIZIERT" for item in checks) else (
            "BLOCKIERT" if any(item["status"] == "BLOCKIERT" for item in checks) else "OFFEN"
        )
        return json.dumps({"status": start_status, "archive_status": "VERIFIZIERT",
                           "archive": str(archive), "sha256": digest, "bytes": archive.stat().st_size,
                           "commit": revision, "files": len(manifest), "manifest_sha256": manifest,
                           "start_checks": checks}, indent=2)
    if action == "PATCH-APPLY":
        if len(normalized) != 4:
            raise DevhubError("PATCH-APPLY requires a candidate path.")
        return _patch_apply(project_id, normalized[3])
    if action not in {"SYSTEMSTART", "WEITER", "CODEFORGE", "SUPERCODEFORGE", "BUILD", "UPDATE"}:
        raise DevhubError(f"Unknown action {action}. Try 666DEV HELP.")
    if action in {"SYSTEMSTART", "UPDATE"}:
        from .desktop_impact import desktop_impact

        head = git(ROOT, "rev-parse", "--verify", "HEAD^{commit}")
        companion = desktop_impact(ROOT, head)
        result = _checkpoint_action(project_id, action)
        return json.dumps({**result, "desktop_impact": companion}, indent=2, ensure_ascii=False)
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
