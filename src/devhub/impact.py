"""Plan test revalidation from repository changes and the project graph."""
from __future__ import annotations

import os
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Any

from .core import ROOT, DevhubError, git, project_entries, python_graph
from .providers import git_bytes


def changed_paths(root: Path, base: str, head: str) -> dict[str, set[str]]:
    """Keep staged, unstaged and committed changes even when they cancel out."""
    changes: dict[str, set[str]] = defaultdict(set)
    for revisions in ((base, head), ("--cached",), ()):
        data = git_bytes(root, "diff", "--no-renames", "--name-status", "-z", *revisions, "--")
        fields = data.rstrip(b"\0").split(b"\0") if data else []
        for status, raw in zip(fields[::2], fields[1::2], strict=True):
            changes[os.fsdecode(raw)].add(status.decode("ascii"))
    untracked = git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z")
    for path in filter(None, untracked.split(b"\0")):
        changes[os.fsdecode(path)].add("?")
    return dict(changes)


def project_impact(state: dict[str, Any], *, base: str | None = None,
                   graph: dict[str, Any] | None = None) -> dict[str, Any]:
    """Report affected declared test files without promoting their evidence."""
    profile, source = state["profile"], state["source"]
    head = state["revision"]["commit"]
    root = Path(git(source, "rev-parse", "--show-toplevel")).resolve()
    prefix = PurePosixPath(source.resolve().relative_to(root).as_posix())
    if base is None:
        for key in ("working", "current"):
            pointer = state[key]["pointer"] if state.get(key) else None
            if pointer and pointer["commit"] != head:
                base = pointer["commit"]
                break
    base = base or head
    if not base or base.startswith("-"):
        raise DevhubError("Impact base must be a Git ref or commit.")
    base = git(root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}")
    changes = changed_paths(root, base, head)
    local = {PurePosixPath(path).relative_to(prefix).as_posix(): flags
             for path, flags in changes.items() if PurePosixPath(path).is_relative_to(prefix)}
    graph = graph if graph is not None else python_graph(source, profile, head)
    tests = sorted(set(profile.get("test_paths", [])))
    declarations = profile.get("test_dependencies", {})
    nodes = {node["id"] for node in graph["nodes"]}
    consumers: dict[str, set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        start, end, kind = edge["from"], edge["to"], edge["direction"]
        if kind == "imports":
            consumers[end].add(start)
        elif kind in {"declares", "targets", "checked_by", "validated_by"}:
            consumers[start].add(end)
    known = nodes | set(consumers)
    uncertain = []
    if profile["source_mode"] == "monorepo" and root == ROOT.resolve():
        hub_inputs = {"registry/projects.json", project_entries()[profile["id"]], ".gitmodules", ".gitattributes"}
        if hub_inputs & changes.keys():
            uncertain.append("project profile, registry or checkout contract changed")
    elif changes:
        uncertain.append("linked checkout cannot establish the historical hub profile")
    if graph["diagnostics"]:
        uncertain.append("graph has unresolved diagnostics")
    if any(flags - {"M"} or path not in known for path, flags in local.items()):
        uncertain.append("source change has no complete graph mapping or changes the file inventory")

    paths_to_tests: dict[str, list[list[str]]] = defaultdict(list)
    for path in sorted(local):
        pending = deque([[path]])
        seen = {path}
        while pending:
            chain = pending.popleft()
            if chain[-1] in tests:
                paths_to_tests[chain[-1]].append(chain)
            for neighbor in sorted(consumers[chain[-1]] - seen):
                seen.add(neighbor)
                pending.append([*chain, neighbor])

    checks = []
    for test in tests:
        chains = paths_to_tests[test]
        if chains:
            disposition, reasons = "RECHECK", ["changed input reaches this test"]
        elif uncertain:
            disposition, reasons = "RECHECK", uncertain
        elif local and test not in declarations:
            disposition, reasons = "RECHECK", ["test has no explicit dependency declaration"]
        else:
            disposition, reasons = "UNIMPACTED", ["no changed input in the declared scope reaches this test"]
        checks.append({"path": test, "disposition": disposition, "chains": chains, "reasons": reasons})
    return {"project_id": profile["id"], "base": base, "head": head,
            "changed_paths": sorted(local), "fallback_reasons": uncertain, "checks": checks}
