"""666DEV Windows host preflight — zero-cost, local only, no mutation of Current.

Writes one diagnostic JSON under ignored .work; never uploads, deploys,
installs tools, runs the UI or requests user secrets.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / ".work" / "host-acceptance"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_BRANCH = "security/666dev-r07-recovery-and-handoff-hardening-20261122"


def run_command(args: list[str], *, cwd: Path, timeout: int = 45) -> dict:
    try:
        p = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                           errors="replace", timeout=timeout, check=False,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        return {"status": "VERIFIZIERT" if p.returncode == 0 else "BLOCKIERT",
                "exit_code": p.returncode, "command": args[0],
                "output_tail": (p.stdout + p.stderr)[-2000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "BLOCKIERT", "exit_code": None, "command": args[0],
                "reason": type(exc).__name__}


def check_host(*, expected_sha: str, root: Path = ROOT) -> dict:
    """Conservative host acceptance; no UI or external network execution."""
    if not SHA_RE.fullmatch(expected_sha):
        raise ValueError("Expected complete lowercase 40-character commit SHA")
    report = {
        "schema": "666dev-windows-host-precheck/v1",
        "authority": "666DEV",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "os": platform.system(),
        "python": platform.python_version(),
        "expected_sha": expected_sha,
        "expected_branch": EXPECTED_BRANCH,
        "working_root": str(root),
        "checks": {},
        "windows_gui_acceptance": "OFFEN",
        "plugin_host_acceptance": "OFFEN",
        "current_updated": False,
        "additional_cost_eur": 0,
    }
    if os.name != "nt":
        report["status"] = "PARTIAL"
        report["reason"] = "Native Windows host required."
        return report
    git_head = run_command(["git", "rev-parse", "HEAD"], cwd=root)
    report["checks"]["git_head"] = git_head
    actual_sha = git_head.get("output_tail", "").strip()
    report["observed_sha"] = actual_sha
    report["checks"]["source_revision"] = {
        "status": "VERIFIZIERT" if git_head["status"] == "VERIFIZIERT"
                  and actual_sha == expected_sha else "CONFLICT_QUARANTINE",
    }
    git_branch = run_command(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=root)
    report["checks"]["git_branch"] = git_branch
    report["checks"]["branch_identity"] = {
        "status": "VERIFIZIERT" if git_branch["status"] == "VERIFIZIERT"
                  and git_branch.get("output_tail", "").strip() == EXPECTED_BRANCH
                  else "CONFLICT_QUARANTINE",
    }
    launcher = root / "windows-app" / "START_666DEV_WINDOWS.cmd"
    if launcher.is_file():
        # Launch from a path with spaces, so no shell/command quoting is inferred.
        cwd = REPORTS / "cwd with spaces"
        cwd.mkdir(parents=True, exist_ok=True)
        run = run_command(["cmd.exe", "/d", "/c", str(launcher), "--check"], cwd=cwd)
    else:
        run = {"status": "BLOCKIERT", "reason": "Windows launcher absent"}
    report["checks"]["launcher_from_spaced_cwd"] = run
    report["status"] = ("PARTIAL" if all(item.get("status") == "VERIFIZIERT"
                                         for item in report["checks"].values())
                        else "BLOCKIERT")
    report["reason"] = ("Preflight passed; interactive GUI and plugin host not tested."
                        if report["status"] == "PARTIAL"
                        else "Preflight failed; no release authorization.")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    report = check_host(expected_sha=args.expected_sha)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / ("WINDOWS_PRECHECK_" + report["expected_sha"][:12] + ".json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(path)},
                     ensure_ascii=False))
    return 0 if report["status"] == "PARTIAL" and os.name == "nt" else 2


if __name__ == "__main__":
    raise SystemExit(main())
