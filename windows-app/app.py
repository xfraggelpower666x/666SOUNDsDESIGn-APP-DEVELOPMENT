"""Lokale Windows-Steuerung für den bestehenden 666DEV-Checkout."""
from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from devhub.core import DevhubError, atomic_json, dashboard_data, project_entries, read_json
from devhub.livecircle import resume, snapshot
from devhub.intelligence.operations import FACETS, build_operations_center
from devhub.intelligence.facet_store import read_checkpoint
from devhub import repo_mind
from devhub.repo_mind_context import inspect_sources
from devhub.visualforms import ASSET_FILES as VISUAL_ASSETS, render_workspace

UI = Path(__file__).resolve().parent / "ui"
CONFIG = ROOT / ".work" / "windows-app" / "settings.json"
DEFAULTS = {"repository": "xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT",
            "ref": "copilot/666dev-initial-functional-setup", "base": "HEAD"}
ACTIONS = ("STATUS", "CONTEXT", "IMPACT", "SYSTEMSTART", "CODEFORGE",
           "SUPERCODEFORGE", "WEITER", "BUILD", "FREEZE", "UPDATE")
ASSETS = {
    "/": (UI / "index.html", "text/html"),
    "/app.css": (UI / "app.css", "text/css"),
    "/app.js": (UI / "app.js", "text/javascript"),
    "/dashboard/": (ROOT / "web" / "index.html", "text/html"),
    "/dashboard/style.css": (ROOT / "web" / "style.css", "text/css"),
    "/dashboard/app.js": (ROOT / "web" / "app.js", "text/javascript"),
}


def valid_ref(value):
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,254}", value)
            or ".." in value or "//" in value or value.endswith(("/", "."))):
        raise ValueError("Ungültiger Git-Ref.")
    return value


def settings_from(data):
    repository = data.get("repository")
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repository):
        raise ValueError("GitHub-Repository im Format owner/repo angeben.")
    return {"repository": repository, "ref": valid_ref(data.get("ref")), "base": valid_ref(data.get("base"))}


def settings():
    return settings_from(read_json(CONFIG)) if CONFIG.is_file() else dict(DEFAULTS)


def run_local(args):
    try:
        done = subprocess.run(args, cwd=ROOT, capture_output=True, encoding="utf-8",
                              errors="replace", timeout=320, check=False,
                              env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1",
                                   "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Der lokale Vorgang hat das Zeitlimit erreicht.") from exc
    return {"exit_code": done.returncode, "stdout": done.stdout[-48000:], "stderr": done.stderr[-12000:]}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def github_probe(data):
    repo = settings()
    token = data.get("token", "")
    if not isinstance(token, str) or len(token) > 512 or any(not 33 <= ord(char) <= 126 for char in token):
        raise ValueError("Ungültiges Tokenformat.")
    expected = data.get("expected_commit", "")
    if not isinstance(expected, str) or (expected and not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", expected)):
        raise ValueError("Erwarteten vollständigen Commit angeben.")
    owner, name = (quote(part, safe="") for part in repo["repository"].split("/"))
    branch = repo["ref"].removeprefix("refs/heads/")
    if expected and (branch == "HEAD" or branch.startswith("refs/")):
        raise ValueError("Für Readback einen GitHub-Branch einstellen.")
    endpoint = (f"git/ref/heads/{quote(branch, safe='/')}" if expected
                else f"commits/{quote(repo['ref'], safe='')}")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "666DEV-Windows",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = build_opener(NoRedirect())
    try:
        with client.open(Request(f"https://api.github.com/repos/{owner}/{name}/{endpoint}",
                                 headers=headers), timeout=12) as response:
            commit = json.load(response)
    except HTTPError as exc:
        return {"status": "OFFEN", "detail": f"GitHub HTTP {exc.code}. Prüfe Repository, Ref und Leserechte."}
    except (URLError, TimeoutError):
        return {"status": "OFFEN", "detail": "GitHub API ist gerade nicht erreichbar."}
    except ValueError:
        commit = None
    if expected and isinstance(commit, dict):
        obj = commit.get("object")
        if commit.get("ref") != f"refs/heads/{branch}" or not isinstance(obj, dict) or obj.get("type") != "commit":
            return {"status": "READBACK_PENDING", "detail": "Der erwartete Branch wurde nicht zurückgelesen."}
        commit = obj
    sha = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(sha, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", sha):
        return {"status": "OFFEN", "detail": "Die GitHub-Antwort enthält keine gültige Commit-ID."}
    result = {"status": "VERIFIZIERT", "repository": repo["repository"], "ref": repo["ref"],
              "commit": sha, "detail": "Commit über die GitHub-API gelesen."}
    if expected:
        match = sha == expected.lower()
        result.update(status="VERIFIZIERT" if match else "PARTIAL", expected_commit=expected.lower(),
                      detail="Branch stimmt mit dem erwarteten Commit überein." if match else
                      "Branch zeigt aktuell auf einen anderen Commit.")
    return result


def repo_mind_action(data):
    action = data.get("action")
    if action == "index":
        return repo_mind.refresh_index(ROOT)
    if action == "context":
        instruction, paths = data.get("instruction", ""), data.get("paths", [])
        if (not isinstance(instruction, str) or len(instruction) > 1000
                or not isinstance(paths, list) or len(paths) > 8
                or any(not isinstance(path, str) or not 1 <= len(path) <= 300 for path in paths)):
            raise ValueError("Unzulässiger Quellauftrag.")
        return inspect_sources(ROOT, instruction, paths)
    base = data.get("base")
    base = valid_ref(base) if base else None
    target = valid_ref(data.get("target"))
    if action == "review":
        return repo_mind.review(ROOT, base, target)
    if action == "publish":
        digest = data.get("review_sha256")
        if not base or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Für die Freigabe werden Umbenennungsbasis und Review-Prüfsumme benötigt.")
        return repo_mind.publish(ROOT, base, target, expected_review=digest)
    raise ValueError("Unbekannte Repo-Mind-Aktion.")


class ControlServer(ThreadingHTTPServer):
    def __init__(self, port):
        super().__init__(("127.0.0.1", port), Handler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.csrf = secrets.token_urlsafe(32)
        self.operation = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, status, content, media, *, policy=None):
        self.send_response(status)
        self.send_header("Content-Type", f"{media}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         policy or "default-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(content)

    def json(self, status, data):
        self.respond(status, json.dumps(data).encode("utf-8"), "application/json")

    def local_host(self):
        return self.headers.get("Host") == urlsplit(self.server.origin).netloc

    def do_GET(self):
        if not self.local_host():
            self.json(403, {"error": "Lokaler Host erforderlich."})
            return
        url = urlsplit(self.path)
        route = url.path
        try:
            if route in ASSETS:
                path, media = ASSETS[route]
                self.respond(200, path.read_bytes(), media)
            elif route == "/visualforms/":
                query = parse_qs(url.query, keep_blank_values=True)
                project, *duplicates = query.get("project", [""])
                if duplicates or (project and project not in project_entries()):
                    self.json(400, {"error": "Unbekanntes Projekt."})
                    return
                nonce = secrets.token_urlsafe(24)
                handoff = query.get("handoff", [])
                checkpoint = None
                if handoff:
                    if len(handoff) != 1 or len(handoff[0]) > 2048:
                        self.json(400, {"error": "Ungültiger UI-Handoff."})
                        return
                    try:
                        checkpoint = json.loads(handoff[0])
                    except ValueError:
                        self.json(400, {"error": "Ungültiger UI-Handoff."})
                        return
                    if not isinstance(checkpoint, dict):
                        self.json(400, {"error": "Ungültiger UI-Handoff."})
                        return
                html = render_workspace(snapshot(project) if project else None, checkpoint)
                html = html.replace("<script>", f'<script nonce="{nonce}">')
                self.respond(200, html.encode("utf-8"), "text/html", policy=(
                    f"default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; "
                    "frame-ancestors 'self'; base-uri 'none'; form-action 'none'; sandbox allow-scripts allow-forms"
                ))
            elif route == "/api/operations-center":
                query = parse_qs(url.query, keep_blank_values=True)
                values = query.get("project", [""])
                if len(values) != 1 or (values[0] and values[0] not in project_entries()):
                    self.json(400, {"error": "Unbekanntes Projekt."})
                    return
                project = values[0]
                native = snapshot(project) if project else None
                records = ({facet_id: read_checkpoint(project, facet_id, native)
                            for facet_id, _, _ in FACETS} if project else {})
                self.json(200, build_operations_center(native, registry=project_entries(),
                                                       facet_records=records))
            elif route == "/dashboard.json":
                self.json(200, dashboard_data())
            elif route == "/api/state":
                git = run_local(["git", "rev-parse", "--verify", "HEAD"])
                self.json(200, {"csrf": self.server.csrf, "config": settings(), "projects": sorted(project_entries()),
                                "checkout": str(ROOT), "head": git["stdout"].strip() if git["exit_code"] == 0 else None})
            else:
                self.json(404, {"error": "Unbekannter Pfad."})
        except (DevhubError, OSError, ValueError) as exc:
            self.json(500, {"error": str(exc)})

    def do_POST(self):
        if (not self.local_host() or self.headers.get("Origin") != self.server.origin
                or not hmac.compare_digest(self.headers.get("X-666DEV-CSRF", "").encode("utf-8"),
                                           self.server.csrf.encode("ascii"))):
            self.json(403, {"error": "Die lokale Anwendungssitzung fehlt."})
            return
        try:
            size = int(self.headers.get("Content-Length", 0))
            if self.headers.get_content_type() != "application/json" or not 0 < size <= 8192:
                raise ValueError("Ungültige Anfrage.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("JSON-Objekt erwartet.")
            route = urlsplit(self.path).path
            if route == "/api/settings":
                config = settings_from(data)
                atomic_json(CONFIG, config)
                self.json(200, config)
            elif route == "/api/github":
                self.json(200, github_probe(data))
            elif route == "/api/livecircle":
                project = data.get("project")
                if not isinstance(project, str) or project not in project_entries():
                    raise ValueError("Unbekanntes Projekt.")
                base = data.get("desktop_base")
                if base is not None:
                    base = valid_ref(base)
                report = (resume(project, data["handoff"], desktop_base=base) if "handoff" in data
                          else snapshot(project, desktop_base=base))
                self.json(200, report)
            elif route == "/api/repo-mind":
                with self.server.operation:
                    self.json(200, repo_mind_action(data))
            elif route == "/api/action":
                with self.server.operation:
                    self.json(200, run_action(data))
            else:
                self.json(404, {"error": "Unbekannter Pfad."})
        except (DevhubError, OSError, ValueError) as exc:
            self.json(400, {"error": str(exc)})


def run_action(data):
    action = data.get("action")
    if action == "GIT":
        return run_local(["git", "--no-optional-locks", "status", "--short", "--branch"])
    if action == "VERIFY":
        return run_local([sys.executable, "-m", "devhub.verifier", f'--base={settings()["base"]}'])
    project = data.get("project")
    if action not in ACTIONS or not isinstance(project, str) or project not in project_entries():
        raise ValueError("Unbekanntes Projekt oder nicht unterstützte Dev-Aktion.")
    if action == "UPDATE" and data.get("confirmed") is not True:
        raise ValueError("Current-Update muss bestätigt werden.")
    args = [sys.executable, "-m", "devhub.cli", "666DEV", project, action]
    if action == "IMPACT":
        # Die standardmäßige Basis des Livecircle beibehalten, sofern kein Ref gewählt wurde.
        base = settings()["base"]
        if base != "HEAD":
            args.append(base)
    return run_local(args)


def open_window(url):
    if os.name == "nt":
        edge = shutil.which("msedge.exe")
        if not edge:
            for variable in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
                folder = os.environ.get(variable)
                if folder and (candidate := Path(folder) / "Microsoft/Edge/Application/msedge.exe").is_file():
                    edge = str(candidate)
                    break
        if edge:
            try:
                subprocess.Popen([edge, f"--app={url}"])
                return
            except OSError:
                pass
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--check", action="store_true", help="Lokalen Startpfad prüfen und beenden")
    args = parser.parse_args()
    if args.check:
        root = run_local(["git", "rev-parse", "--show-toplevel"])
        revision = run_local(["git", "rev-parse", "--verify", "HEAD"])
        missing = sorted(route for route, (file, _) in ASSETS.items() if not file.is_file())
        missing.extend(str(path.relative_to(ROOT)) for path in VISUAL_ASSETS if not path.is_file())
        ready = (root["exit_code"] == revision["exit_code"] == 0
                 and Path(root["stdout"].strip()).resolve() == ROOT and not missing)
        print(json.dumps({"status": "VERIFIZIERT" if ready else "BLOCKIERT",
                          "python": sys.version.split()[0], "git_commit": revision["stdout"].strip(),
                          "missing_assets": missing}))
        if not ready:
            raise SystemExit(2)
        return
    with ControlServer(args.port) as server:
        print(f"666DEV Windows Control: {server.origin}", flush=True)
        if not args.no_window:
            open_window(server.origin)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
