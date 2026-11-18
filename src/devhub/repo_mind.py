"""Repository hygiene from a committed tree, with isolated Markdown-only repairs."""
from __future__ import annotations

import json
import posixpath
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from .core import DevhubError, atomic_json, git
from .providers import LocalGitProvider, git_bytes

REPOSITORY = "xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT"
INDEX = ".work/repo-mind/file-index.json"
RULES = "registry/repo-mind.json"
# Standard one-line destinations and reference definitions.
LINK = re.compile(r"(?<!\\)\[[^\[\]\n]*\]\(\s*(?:<(?P<angle>[^<>\n]+)>|(?P<plain>[^\s()<>`]+))(?=[\s)])")
REFERENCE = re.compile(r"^ {0,3}\[[^\]\n]+\]:\s*(?:<(?P<angle>[^<>\n]+)>|(?P<plain>[^\s()<>`]+))")


def inventory(root: Path, revision: str) -> dict[str, tuple[str, str]]:
    entries = git_bytes(root, "ls-tree", "-r", "-z", revision).decode("utf-8").split("\0")
    files = {}
    for entry in filter(None, entries):
        metadata, path = entry.split("\t", 1)
        mode, _, oid = metadata.split()
        files[path] = (mode, oid)
    return files


def committed_rules(provider: LocalGitProvider, head: str) -> dict:
    rules = json.loads(provider.read_file(head, RULES))
    if (not isinstance(rules, dict) or rules.get("schema_version") != 1
            or rules.get("generated_index") != INDEX
            or any(not isinstance(rules.get(key), list) or
                   any(not isinstance(x, str) or not re.fullmatch(r"[.A-Za-z0-9_/-]+", x)
                       or ".." in x.split("/") for x in rules[key])
                   for key in ("required_roots", "allowed_roots", "auto_link_sources"))):
        raise DevhubError("Ungültige Repo-Mind-Regeln.")
    return rules


def markdown_candidates(content: str):
    offset = 0
    fence = None
    comment = False
    frontmatter = False
    for number, line in enumerate(content.splitlines(keepends=True), 1):
        start, offset = offset, offset + len(line)
        if number == 1 and line.strip() == "---":
            frontmatter = True
            continue
        if frontmatter:
            frontmatter = line.strip() not in {"---", "..."}
            continue
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if comment or "<!--" in line:
            comment = line.rfind("<!--") > line.rfind("-->") if "<!--" in line else "-->" not in line
            continue
        if marker:
            fence = marker[1]
            continue
        if "`" in line or line.startswith(("    ", "\t", ">")):
            continue
        for match in list(LINK.finditer(line)) + list(REFERENCE.finditer(line)):
            group = "angle" if match["angle"] is not None else "plain"
            yield number, start + match.start(group), start + match.end(group), match[group]


def resolve_link(source: str, link: str) -> str | None:
    try:
        url = urlsplit(link)
    except ValueError:
        return None
    if url.scheme or url.netloc or not url.path or url.path.startswith("/") or "\\" in link:
        return None
    target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(url.path)))
    return target if target != ".." and not target.startswith("../") else None


def scope(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:2]) if parts[0] == "projects" else "hub"


def scan(root: Path, baseline: str | None = None) -> tuple[dict, dict[str, str]]:
    provider = LocalGitProvider(root)
    head = provider.read_commit("HEAD")
    base = provider.read_commit(baseline) if baseline is not None else None
    if base:
        git(root, "merge-base", "--is-ancestor", base, head)
    rules = committed_rules(provider, head)
    files = inventory(root, head)
    directories = {str(parent) for name in files for parent in PurePosixPath(name).parents}
    roots = {name.split("/", 1)[0] for name in files}
    findings = [
        {"rule": "missing-root", "path": path, "disposition": "REVIEW"}
        for path in sorted(set(rules["required_roots"]) - directories)
    ] + [
        {"rule": "unexpected-root", "path": path, "disposition": "REVIEW"}
        for path in sorted(roots - set(rules["allowed_roots"]))
    ]
    edits = {}
    former = inventory(root, base) if base else {}
    regular = {"100644", "100755"}
    old_counts = Counter(blob for mode, blob in former.values() if mode in regular)
    locations = {}
    for path, (mode, blob) in files.items():
        if mode in regular:
            locations.setdefault(blob, []).append(path)
    eligible_fixes = 0
    for source, (mode, _) in files.items():
        if mode not in regular or not source.lower().endswith(".md"):
            continue
        try:
            content = provider.read_file(head, source).decode("utf-8")
        except UnicodeDecodeError:
            findings.append({"rule": "markdown-encoding", "path": source, "disposition": "REVIEW"})
            continue
        changes = []
        for line, start, end, link in markdown_candidates(content):
            target = resolve_link(source, link)
            if target is None or target in files or target in directories:
                continue
            previous = former.get(target)
            old_blob = previous[1] if previous and previous[0] in regular else None
            matches = locations.get(old_blob, [])
            candidate = matches[0] if old_counts[old_blob] == 1 and len(matches) == 1 else None
            permitted = (
                candidate is not None and candidate not in former
                and all(path.lower().endswith(".md") for path in (target, candidate))
                and scope(source) == scope(target) == scope(candidate)
                and scope(source) == "hub"
                and any(source.startswith(item) if item.endswith("/") else source == item
                        for item in rules["auto_link_sources"])
            )
            finding = {"rule": "broken-markdown-link", "path": source, "line": line,
                       "target": target, "disposition": "PR_FIX" if permitted else "REVIEW"}
            if candidate:
                finding.update(candidate=candidate, blob=old_blob)
            if permitted:
                url = urlsplit(link)
                replacement = quote(posixpath.relpath(candidate, posixpath.dirname(source) or "."), safe="/")
                replacement += ("?" + url.query if url.query else "") + ("#" + url.fragment if url.fragment else "")
                if resolve_link(source, replacement) != candidate:
                    raise DevhubError("Linkziel konnte nicht verifiziert werden.")
                changes.append((start, end, replacement))
                eligible_fixes += 1
            findings.append(finding)
        for start, end, replacement in sorted(set(changes), reverse=True):
            content = content[:start] + replacement + content[end:]
        if changes:
            edits[source] = content
    return {"authority": "666DEV", "component": "666REPO-MIND", "commit": head,
            "rename_base": base, "findings": findings, "eligible_fixes": eligible_fixes}, edits


def refresh_index(root: Path) -> dict:
    provider = LocalGitProvider(root)
    head = provider.read_commit("HEAD")
    committed_rules(provider, head)
    output = root / INDEX
    if output.resolve() != output or not output.resolve().is_relative_to(root):
        raise DevhubError("Unsicherer Indexpfad.")
    files = inventory(root, head)
    if INDEX in files:
        raise DevhubError("Der generierte Index muss außerhalb des versionierten Dateibaums liegen.")
    index = {"schema_version": 1, "generated": True, "commit": head,
             "files": [{"path": path, "mode": mode, "oid": oid} for path, (mode, oid) in files.items()]}
    git(root, "check-ignore", "--", INDEX)
    atomic_json(output, index)
    if json.loads(output.read_bytes()) != index:
        raise DevhubError("Readback des generierten Index fehlgeschlagen.")
    return {"status": "VERIFIZIERT", "path": INDEX, "commit": head, "files": len(files)}


def gh(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["gh", *args], cwd=root, capture_output=True, text=True,
                                check=True, timeout=90)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise DevhubError("GitHub-CLI-Aufruf fehlgeschlagen. Prüfe Anmeldung, Rechte und vorhandene PRs.") from exc
    return result.stdout.strip()


def publish(root: Path, baseline: str, target: str) -> dict:
    report, edits = scan(root, baseline)
    if not edits:
        return {**report, "status": "NO_CHANGES"}
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", target):
        raise DevhubError("Ungültiger Zielbranch.")
    git(root, "check-ref-format", f"refs/heads/{target}")
    origin = git(root, "remote", "get-url", "--push", "origin").removesuffix(".git")
    if origin not in {f"https://github.com/{REPOSITORY}", f"git@github.com:{REPOSITORY}"}:
        raise DevhubError("Repo Mind darf nur an das bestätigte 666DEV-Repository veröffentlichen.")
    head = report["commit"]
    branch = f"666repo-mind/links-{head[:16]}-{report['rename_base'][:16]}"
    head_ref, target_ref = f"refs/heads/{branch}", f"refs/heads/{target}"
    if target == branch or git(root, "ls-remote", "--refs", "origin", target_ref).split() != [head, target_ref]:
        raise DevhubError("Der GitHub-Zielbranch entspricht nicht dem geprüften Checkout.")
    existing = json.loads(gh(root, "pr", "list", "--repo", REPOSITORY, "--base", target,
                             "--head", branch, "--state", "open", "--json", "url,headRefOid"))
    if len(existing) > 1:
        raise DevhubError("Mehrere offene PRs für denselben Korrekturbranch.")
    with tempfile.TemporaryDirectory(prefix="666repo-mind-") as directory:
        worktree = Path(directory) / "worktree"
        git(root, "worktree", "add", "--detach", str(worktree), head)
        try:
            for path, content in edits.items():
                destination = worktree / path
                if destination.resolve() != destination or not destination.is_file():
                    raise DevhubError("Unerwartetes Ziel im isolierten Worktree.")
                destination.write_bytes(content.encode("utf-8"))
            git(worktree, "add", "--", *edits)
            git(worktree, "diff", "--cached", "--check")
            paths = git_bytes(worktree, "diff", "--cached", "--name-only", "-z").decode().split("\0")
            if set(filter(None, paths)) != set(edits):
                raise DevhubError("Der PR-Diff entspricht nicht den überprüften Linkkorrekturen.")
            git(worktree, "commit", "-m", "Fix verified internal Markdown links")
            tree = git(worktree, "rev-parse", "HEAD^{tree}")
            remote = git(root, "ls-remote", "--refs", "origin", head_ref).split()
            if remote:
                git(root, "fetch", "--no-tags", "origin", head_ref)
                if (git(root, "rev-parse", "FETCH_HEAD") != remote[0]
                        or git(root, "rev-parse", "FETCH_HEAD^") != head
                        or git(root, "rev-parse", "FETCH_HEAD^{tree}") != tree):
                    raise DevhubError("Vorhandener Repo-Mind-Branch enthält einen anderen Stand.")
            elif not existing:
                git(worktree, "push", "origin", f"HEAD:{head_ref}")
            if existing:
                if remote != [existing[0]["headRefOid"], head_ref]:
                    raise DevhubError("PR-Head stimmt nicht mit dem verifizierten Korrekturbranch überein.")
                return {**report, "status": "EXISTING_PR", "url": existing[0]["url"]}
            if git(root, "ls-remote", "--refs", "origin", target_ref).split() != [head, target_ref]:
                raise DevhubError("Der Zielbranch hat sich geändert. PR nach neuem Abgleich erstellen.")
            url = gh(root, "pr", "create", "--repo", REPOSITORY, "--base", target,
                     "--head", branch, "--title", "666REPO-MIND · Markdown-Links",
                     "--body", f"Identische Zielblobs aus Git belegt. Basis: {head}. "
                     f"Linkkorrekturen: {report['eligible_fixes']}.")
            return {**report, "status": "PR_CREATED", "url": url}
        finally:
            git(root, "worktree", "remove", "--force", str(worktree))
