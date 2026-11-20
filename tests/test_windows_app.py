import importlib.util
import io
import json
import re
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

APP_PATH = Path(__file__).resolve().parents[1] / "windows-app" / "app.py"
SPEC = importlib.util.spec_from_file_location("windows_control", APP_PATH)
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class WindowsAppTest(unittest.TestCase):
    def setUp(self):
        workspace = self.enterContext(tempfile.TemporaryDirectory())
        self.config = Path(workspace) / "settings.json"
        self.enterContext(patch.object(app, "CONFIG", self.config))
        self.server = self.enterContext(app.ControlServer(0))
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)
        self.client = HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        self.addCleanup(self.client.close)

    def request(self, path, data=None, **headers):
        body = None if data is None else json.dumps(data)
        if body is not None:
            headers["Content-Type"] = "application/json"
        self.client.request("GET" if body is None else "POST", path, body, headers)
        reply = self.client.getresponse()
        return reply.status, reply.read()

    def session(self):
        status, body = self.request("/api/state")
        self.assertEqual(status, 200)
        state = json.loads(body)
        self.assertTrue(state["head"])
        self.assertTrue(state["projects"])
        return state, {"Origin": self.server.origin, "X-666DEV-CSRF": state["csrf"]}

    def test_dashboard_and_local_controls(self):
        for path in ("/", "/app.css", "/app.js", "/dashboard/", "/dashboard/style.css", "/dashboard/app.js"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 200)
        self.assertIn("projects", json.loads(self.request("/dashboard.json")[1]))
        self.assertEqual(self.request("/api/state", Host="external.example")[0], 403)
        state, headers = self.session()
        self.assertEqual(self.request("/api/action", {"action": "GIT"})[0], 403)
        status, result = self.request("/api/action", {"action": "GIT"}, **headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(result)["exit_code"], 0)
        status, result = self.request("/api/action", {"action": "UPDATE", "project": state["projects"][0]}, **headers)
        self.assertEqual(status, 400)
        self.assertIn("bestätigt", json.loads(result)["error"])

    def test_operations_center_is_native_read_only_and_local(self):
        self.assertEqual(403, self.request("/api/operations-center", Host="external.example")[0])
        self.assertEqual(400, self.request("/api/operations-center?project=unknown")[0])
        self.assertEqual(400, self.request("/api/operations-center?project=demo-monorepo&project=demo-linked")[0])
        status, body = self.request("/api/operations-center")
        self.assertEqual(200, status)
        overview = json.loads(body)
        self.assertEqual("OFFEN", overview["status"])
        self.assertFalse(overview["visual_daemon"]["can_autowrite"])
        self.assertIsNone(overview["project_id"])
        status, body = self.request("/api/operations-center?project=demo-monorepo")
        self.assertEqual(200, status)
        result = json.loads(body)
        native = app.snapshot("demo-monorepo")
        self.assertEqual(native["status"], result["status"])
        self.assertEqual(native["source_commit"], result["source"]["source_commit"])
        self.assertEqual(6, len(result["facets"]))
        self.assertEqual("OFFEN", result["host_acceptance"])
        self.assertFalse(result["visual_daemon"]["can_run_background"])
        self.assertIn(b"Operations Center", self.request("/")[1])

    def test_visualforms_uses_local_native_evidence_and_is_read_only(self):
        self.assertEqual(403, self.request("/visualforms/", Host="external.example")[0])
        self.assertEqual(400, self.request("/visualforms/?project=unknown")[0])
        self.assertEqual(400, self.request("/visualforms/?project=&project=demo-monorepo")[0])
        self.client.request("GET", "/visualforms/?project=demo-monorepo")
        response = self.client.getresponse()
        body = response.read().decode()
        self.assertEqual(200, response.status)
        policy = response.getheader("Content-Security-Policy")
        self.assertIn("sandbox allow-scripts allow-forms", policy)
        self.assertIn("default-src 'none'", policy)
        nonce = re.search(r"script-src 'nonce-([^']+)'", policy)[1]
        self.assertIn(f'<script nonce="{nonce}">', body)
        self.assertNotIn("<script>", body)
        payload = json.loads(re.search(r'data-ui-data>(.*?)</script>', body)[1])
        native = app.snapshot("demo-monorepo")
        self.assertEqual(native["source_commit"], payload["companion"]["source_revision"])
        self.assertEqual(native["status"], payload["views"][0]["status"])
        self.assertEqual("neutral", payload["handoff_format"])
        self.assertNotIn(str(app.ROOT), body)
        status, empty = self.request("/visualforms/")
        self.assertEqual(200, status)
        self.assertIn("Projektquelle offen", empty.decode())

    def test_visual_handoff_binds_the_form_to_the_native_revision(self):
        project = "demo-monorepo"
        revision = app.snapshot(project)["source_commit"]
        handoff = {"schema": "scevi.visual.handoff.1", "project_key": "666dev:" + project,
                   "source_revision": revision, "mode": "formats", "format_id": "iceberg"}
        def read(data):
            query = urlencode({"project": project, "handoff": json.dumps(data)})
            status, body = self.request("/visualforms/?" + query)
            self.assertEqual(200, status)
            return body.decode()

        self.assertIn('"start_format":"iceberg"', read(handoff))
        stale = read({**handoff, "source_revision": "0" * 40})
        self.assertNotIn('"start_format":"iceberg"', stale)
        self.assertIn("stimmt nicht mit der Projektbasis überein", stale)
        self.assertNotIn('"start_format":"iceberg"', read({**handoff, "project_key": "anderes-projekt"}))

    def test_github_readback_compares_the_exact_branch(self):
        commit = "a" * 40
        ref = app.DEFAULTS["ref"]
        def check(expected, observed_ref):
            data = {"ref": observed_ref, "object": {"type": "commit", "sha": commit}}
            with patch.object(app, "build_opener") as opener:
                client = opener.return_value
                client.open.return_value = io.BytesIO(json.dumps(data).encode())
                result = app.github_probe({"expected_commit": expected})
                self.assertTrue(client.open.call_args.args[0].full_url.endswith(f"/git/ref/heads/{ref}"))
                return result

        self.assertEqual("VERIFIZIERT", check(commit, "refs/heads/" + ref)["status"])
        mismatch = check("b" * 40, "refs/heads/" + ref)
        self.assertEqual("PARTIAL", mismatch["status"])
        self.assertEqual(commit, mismatch["commit"])
        self.assertEqual("READBACK_PENDING", check(commit, "refs/tags/" + ref)["status"])

    def test_livecircle_shares_native_result(self):
        _, headers = self.session()
        data = {"project": "demo-monorepo"}
        self.assertEqual(self.request("/api/livecircle", data)[0], 403)
        status, result = self.request("/api/livecircle", data, **headers)
        self.assertEqual(status, 200)
        handoff = json.loads(result)
        self.assertEqual(handoff, app.snapshot(data["project"]))
        status, explicit = self.request("/api/livecircle", {**data, "desktop_base": "HEAD"}, **headers)
        self.assertEqual(200, status)
        windows = json.loads(explicit)["desktop_impact"]
        self.assertEqual("EXPLICIT", windows["basis"])
        self.assertEqual(handoff["hub_commit"], windows["base"])
        self.assertEqual("OFFEN", windows["windows_acceptance"])
        status, result = self.request("/api/livecircle", {**data, "handoff": handoff}, **headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(result)["livecircle"], handoff)
        self.assertEqual("MATCHES_HANDOFF", json.loads(result)["recovery"]["context"]["state"])
        foreign = {**handoff, "authority": "foreign"}
        status, result = self.request("/api/livecircle", {**data, "handoff": foreign}, **headers)
        self.assertEqual(200, status)
        self.assertEqual({"state": "CONFLICT_QUARANTINE"}, json.loads(result)["recovery"]["project"])

    def test_repo_mind_is_local_and_uses_native_review(self):
        state, headers = self.session()
        path = "/api/repo-mind"
        context = {"action": "context", "paths": ["src/devhub/cli.py", "../unavailable.py"]}
        self.assertEqual(self.request(path, context)[0], 403)
        status, body = self.request(path, context, **headers)
        self.assertEqual(200, status)
        source = json.loads(body)
        self.assertEqual(state["head"], source["commit"])
        self.assertEqual("python_ast", source["files"][0]["analysis"])
        self.assertEqual("unavailable", source["skipped"][0]["reason"])
        target = "main"
        status, body = self.request(path, {"action": "review", "target": target}, **headers)
        self.assertEqual(200, status)
        self.assertEqual(app.repo_mind.review(app.ROOT, None, target), json.loads(body))
        status, body = self.request(path, {"action": "publish", "target": target, "base": "HEAD",
                                           "review_sha256": "0" * 64}, **headers)
        self.assertEqual(400, status)
        self.assertIn("erneut", json.loads(body)["error"])

    def test_settings_and_token_are_separate(self):
        _, headers = self.session()
        saved = {"repository": "example/dev", "ref": "feature/release", "base": "main"}
        status, _ = self.request("/api/settings", {**saved, "token": "test-token"}, **headers)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(self.config.read_text()), saved)
        with patch.object(app, "build_opener") as opener:
            sha = "b" * 40
            opener.return_value.open.return_value = io.BytesIO(json.dumps({"sha": sha}).encode())
            status, body = self.request("/api/github", {"token": "test-token"}, **headers)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["commit"], sha)
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.github.com/repos/example/dev/commits/feature%2Frelease")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            self.assertNotIn(b"test-token", body)
        self.assertEqual(json.loads(self.config.read_text()), saved)
