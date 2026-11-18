"""Scope Windows companion verification to the 666DEV hub and a Git comparison."""
from __future__ import annotations

from pathlib import Path

from .core import DevhubError, git
from .impact import changed_paths
from .providers import LocalGitProvider

# Sources read by Windows Control, or contracts that affect its entry and UI.
CONTRACTS = (
    ("src/devhub/cli.py", "Befehle und Rückgaben der Windows-Steuerung"),
    ("src/devhub/livecircle.py", "LiveCircle und Handoff"),
    ("src/devhub/recovery.py", "Wiederaufnahme und Projektprüfung im LiveCircle"),
    ("src/devhub/desktop_impact.py", "Windows-Abgleich im LiveCircle"),
    ("src/devhub/repo_mind.py", "Repo-Mind-Ansicht und Freigabe"),
    ("src/devhub/repo_mind_context.py", "Repo-Mind-Quellkontext"),
    ("src/devhub/", "Gemeinsamer Python-Kern"),
    ("registry/", "Projektwahl und Repo-Mind-Regeln"),
    ("schemas/", "Projekt- und Zustandsverträge"),
    ("web/", "Eingebettetes Dashboard"),
    ("pyproject.toml", "Python- und Paketvorgaben"),
)


def contract(path: str) -> str | None:
    for prefix, area in CONTRACTS:
        if path == prefix or (prefix.endswith("/") and path.startswith(prefix)):
            return area
    if path.startswith("projects/") and path.endswith("/project.json"):
        return "Projektprofil und verfügbare Entwicklungsaktionen"
    return None


def desktop_impact(root: Path, head: str, base: str | None = None) -> dict:
    """Read the affected Windows contracts without claiming the app was updated."""
    mode = "EXPLICIT" if base is not None else "FIRST_PARENT"
    result = {"companion": "666DEV Windows Control", "head": head, "base": None,
              "basis": mode, "status": "READBACK_PENDING", "live_changes": [],
              "desktop_changes": [], "windows_acceptance": "OFFEN"}
    try:
        provider = LocalGitProvider(root)
        start = provider.read_commit(f"{head}^1" if base is None else base)
        git(root, "merge-base", "--is-ancestor", start, head)
        changes = changed_paths(root, start, head)
    except (DevhubError, OSError):
        return {**result, "reason": "Kein belegter Git-Vorgänger. Prüfbasis der Windows-App angeben."}

    live = []
    desktop = []
    for path in sorted(changes):
        if path.startswith("windows-app/") and not path.lower().endswith(".md"):
            desktop.append(path)
        elif area := contract(path):
            live.append({"path": path, "area": area})
    return {**result, "base": start, "live_changes": live[:16], "desktop_changes": desktop[:16],
            "live_count": len(live), "desktop_count": len(desktop),
            "status": "WINDOWS_REVIEW_REQUIRED" if live or desktop else "NO_IMPACT_IN_DIFF"}
