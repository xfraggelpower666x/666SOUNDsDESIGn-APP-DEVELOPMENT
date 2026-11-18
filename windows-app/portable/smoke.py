"""Prüft den entpackten Portable-Build auf einem Windows-Host."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.request import Request, urlopen
from zipfile import ZipFile


def wait_for_origin(process: subprocess.Popen, log: Path) -> str:
    deadline = monotonic() + 25
    while monotonic() < deadline:
        output = log.read_text(encoding="utf-8", errors="replace")
        if match := re.search(r"http://127\.0\.0\.1:\d+", output):
            return match[0]
        if process.poll() is not None:
            raise RuntimeError(f"666DEV exited before serving HTTP: {output}")
        sleep(0.1)
    raise TimeoutError("666DEV did not start within 25 seconds.")


def exercise(origin: str, folder: Path, expected_revision: str) -> None:
    def get(path: str) -> str:
        with urlopen(origin + path, timeout=15) as response:
            return response.read().decode("utf-8")

    state = json.loads(get("/api/state"))
    assert state["head"] == expected_revision, state
    assert "demo-monorepo" in state["projects"], state
    html = get("/")
    mind = html.partition('data-panel="repo-mind"')[2].partition("</section>")[0]
    assert 'data-mind-view="chat-archive"' in mind
    assert 'id="chat-import"' in mind

    def post(path: str, data: dict) -> dict:
        headers = {"Origin": origin, "X-666DEV-CSRF": state["csrf"], "Content-Type": "application/json"}
        with urlopen(Request(origin + path, json.dumps(data).encode(), headers), timeout=25) as response:
            return json.load(response)

    dev = post("/api/action", {"action": "STATUS", "project": "demo-monorepo"})
    assert dev["exit_code"] == 0, dev

    fixture = folder / "Test Chat Export.json"
    fixture.write_text(json.dumps({"object": "chatgpt.export", "data": [{
        "id": "test-chat", "title": "Windows Portable", "messages": [
            {"role": "user", "content": "Geprüfter Repo-Mind-Chat"}
        ]
    }]}), encoding="utf-8")
    route = "/api/chat-archive"
    imported = post(route, {"action": "IMPORT", "path": str(fixture)})
    assert imported["added"] == 1, imported
    hits = post(route, {"action": "SEARCH", "query": "repo-mind-chat"})["results"]
    assert len(hits) == 1, hits
    exported = post(route, {"action": "EXPORT", "key": hits[0]["key"]})
    assert "Geprüfter Repo-Mind-Chat" in exported["markdown"]


def test_package(package: Path, expected_revision: str) -> None:
    with TemporaryDirectory(prefix="666DEV Windows smoke ") as work:
        working = Path(work)
        with ZipFile(package) as archive:
            archive.extractall(working)
        install = working / "666DEV Windows x64"
        exe = install / "666DEV.exe"
        info = json.loads((install / "BUILD-INFO.json").read_text(encoding="utf-8"))
        assert info["commit"] == expected_revision, info
        # Ein fremdes Arbeitsverzeichnis sowie Leerzeichen in allen Bundle-Pfaden.
        # Kein vorinstalliertes Git oder Python bei der Werkzeugauflösung.
        env = {**os.environ, "PATH": str(Path(os.environ["SystemRoot"]) / "System32")}
        check = subprocess.run([exe, "--check"], cwd=working, env=env,
                               check=True, capture_output=True, text=True, timeout=25)
        assert json.loads(check.stdout)["git_commit"] == expected_revision, check.stdout
        invalid = subprocess.run([exe, "--invalid-argument"], cwd=working, env=env,
                                 capture_output=True, timeout=25)
        assert invalid.returncode == 2, invalid
        for relative in ("runtime/git/cmd/git.exe", "runtime/gh/bin/gh.exe"):
            subprocess.run([install / relative, "--version"], cwd=working, env=env, check=True, timeout=25)

        log = working / "startup.log"
        with log.open("wb") as output, subprocess.Popen(
            [exe, "--no-window", "--port", "0"], cwd=working, env=env, stdout=output, stderr=subprocess.STDOUT
        ) as process:
            try:
                exercise(wait_for_origin(process, log), working, expected_revision)
            finally:
                if process.poll() is None:
                    subprocess.run(["taskkill.exe", "/F", "/T", "/PID", str(process.pid)],
                                   capture_output=True, timeout=20, check=False)
                    process.wait(timeout=10)
        print("Windows Portable: EXE, Diagnose, CLI, Repo Mind und Archiv-Rundlauf bestanden.")


if __name__ == "__main__":
    test_package(Path(sys.argv[1]).resolve(), sys.argv[2])
