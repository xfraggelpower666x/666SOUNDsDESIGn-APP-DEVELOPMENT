"""Revisionsgebundene Quellenauswahl und statische Python-Fundstellen."""

import ast
import re
from pathlib import PurePosixPath

from .core import DevhubError
from .providers import LocalGitProvider, git_bytes
from .repo_mind import inventory

WORDS = re.compile(r"[^\W_]+")
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "websocket"}


def words(value):
    # CamelCase und Unterstriche in Pfaden werden wie Wörter in der Anfrage behandelt.
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return set(WORDS.findall(separated.casefold()))


def rank_paths(paths, instruction):
    query = {token for token in words(instruction) if len(token) >= 2}
    normalized = instruction.casefold()

    def score(path):
        stem = PurePosixPath(path).stem
        normalized_path = path.casefold()
        explicit = normalized_path in normalized and re.search(
            r"(?<![\w./-])" + re.escape(normalized_path) + r"(?![\w./-])", normalized
        )
        return (
            -bool(explicit),
            -len(query & words(stem)),
            -len(query & words(path)),
            path,
        )

    return sorted(paths, key=score)


def source_evidence(path, text, sha):
    result = {"path": path, "blob_sha": sha, "analysis": "text_only", "symbols": [], "imports": [], "routes": []}
    if PurePosixPath(path).suffix != ".py":
        return result
    try:
        tree = ast.parse(text, filename=path)
    except (SyntaxError, ValueError, RecursionError):
        result["analysis"] = "parse_failed"
        return result

    result["analysis"] = "python_ast"
    definitions = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Import, ast.ImportFrom)
    nodes = sorted((node for node in ast.walk(tree) if isinstance(node, definitions)), key=lambda node: node.lineno)
    for node in nodes:
        if isinstance(node, ast.Import):
            result["imports"].extend({"target": item.name, "line": node.lineno} for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            result["imports"].append({
                "target": "." * node.level + (node.module or ""), "line": node.lineno,
                "names": [item.name for item in node.names[:24]],
            })
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            result["symbols"].append({"name": node.name, "kind": kind, "line": node.lineno, "end_line": node.end_lineno})
            if kind == "function":
                for decorator in node.decorator_list:
                    if route := literal_route(decorator, node.name):
                        result["routes"].append(route)

    result["truncated"] = any(len(result[key]) > 24 for key in ("symbols", "imports", "routes"))
    for key in ("symbols", "imports", "routes"):
        result[key] = result[key][:24]
    return result


def literal_route(decorator, symbol):
    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
        return None
    method = decorator.func.attr
    receiver = decorator.func.value
    if method not in HTTP_METHODS or not isinstance(receiver, ast.Name):
        return None
    path = decorator.args[0] if decorator.args else next(
        (keyword.value for keyword in decorator.keywords if keyword.arg == "path"), None
    )
    if (
        not isinstance(path, ast.Constant) or not isinstance(path.value, str)
        or not path.value.startswith("/") or len(path.value) > 240
        or any(ord(char) < 32 or ord(char) == 127 for char in path.value)
    ):
        return None
    return {
        "kind": "decorator_candidate", "receiver": receiver.id, "method": method.upper(),
        "path": path.value, "symbol": symbol, "line": decorator.lineno,
    }


def inspect_sources(root, instruction, paths):
    """Inspect a bounded set of committed sources, using the 666DEV Git provider."""
    provider = LocalGitProvider(root)
    head = provider.read_commit("HEAD")
    tree = git_bytes(root, "rev-parse", f"{head}^{{tree}}").decode("ascii").strip()
    available = {
        path: oid for path, (mode, oid) in inventory(root, head).items()
        if mode in {"100644", "100755"} and PurePosixPath(path).suffix.lower()
        in {".py", ".js", ".ts", ".json", ".toml", ".md", ".html", ".css", ".yml", ".yaml", ".cmd", ".bat"}
    }
    selected = paths or rank_paths(available, instruction)[:8]
    files, skipped = [], []
    remaining = 256 * 1024
    for path in dict.fromkeys(selected):
        oid = available.get(path)
        if oid is None:
            skipped.append({"path": path, "reason": "unavailable"})
            continue
        size = int(git_bytes(root, "cat-file", "-s", oid))
        if size > min(remaining, 96 * 1024):
            skipped.append({"path": path, "reason": "context_budget"})
            continue
        raw = provider.read_file(head, path)
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            skipped.append({"path": path, "reason": "unsupported_text"})
            continue
        remaining -= len(raw)
        files.append(source_evidence(path, content, oid))
    if provider.read_commit("HEAD") != head:
        raise DevhubError("HEAD hat sich geändert. Quellkontext erneut prüfen.")
    return {"commit": head, "tree": tree, "files": files, "skipped": skipped}
