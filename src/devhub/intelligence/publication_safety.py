"""Prevent previously exposed private plugin payloads from public commits.

This module examines tracked path names only. Never reads or publishes private
file bytes, credentials, archives or hidden plugin implementation.
"""
from __future__ import annotations

import subprocess
from pathlib import PurePosixPath

FORBIDDEN_PREFIXES = (
    ".github/references/coding-profi-v087-source/",
    ".github/coding-control-plugin-snapshot/",
)
FORBIDDEN_FILES = frozenset({
    "666dev-coding-control.zip",
    "l.y.v.r.a. coding profi (6)(1).zip",
})


def forbidden_tracked_paths(paths: list[str]) -> list[str]:
    blocked = []
    for original in paths:
        if not isinstance(original, str):
            continue
        path = original.replace("\\", "/").lstrip("./").casefold()
        if (any(path.startswith(prefix.casefold()) for prefix in FORBIDDEN_PREFIXES)
                or PurePosixPath(path).name in FORBIDDEN_FILES):
            blocked.append(original)
    return sorted(set(blocked))


def preflight() -> int:
    """Fail closed when public HEAD tracks known private plugin-source paths."""
    check = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD"],
                           check=False, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if check.returncode != 0:
        print("WRITE_BLOCKED: cannot inspect committed Git tree")
        return 2
    bad = forbidden_tracked_paths(check.stdout.splitlines())
    if bad:
        # Print path names only, never their contents.
        print("WRITE_BLOCKED: private plugin-source paths tracked in public HEAD:")
        for path in bad:
            print("  " + path)
        return 2
    print("VERIFIZIERT: known private plugin-source paths absent from committed HEAD")
    return 0


if __name__ == "__main__":
    raise SystemExit(preflight())
