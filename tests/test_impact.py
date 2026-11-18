import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub import core, impact, verifier
from devhub.cli import execute


class ImpactTests(unittest.TestCase):
    def test_cli_dashboard_and_verifier_agree_after_start_script_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shutil.copytree(core.ROOT / "registry", root / "registry")
            shutil.copytree(core.ROOT / "projects", root / "projects",
                            ignore=shutil.ignore_patterns("state", "__pycache__"))
            core.git(root, "init", "-q")
            core.git(root, "config", "user.email", "test@example.invalid")
            core.git(root, "config", "user.name", "666DEV test")
            core.git(root, "add", ".")
            core.git(root, "commit", "-qm", "Baseline")
            base = core.git(root, "rev-parse", "HEAD")
            with patch.multiple(core, ROOT=root, REGISTRY=root / "registry" / "projects.json",
                                WORK=root / ".work"), patch.object(impact, "ROOT", root),                     patch.object(verifier, "ROOT", root):
                project_id = "demo-monorepo"
                execute(["666DEV", project_id, "SYSTEMSTART"])
                app = root / "projects" / project_id / "app"
                script = app / "src" / "demo_app" / "main.py"
                script.write_text(script.read_text(encoding="utf-8") + "\n# New start behavior\n",
                                  encoding="utf-8")
                core.git(root, "add", str(script))
                core.git(root, "commit", "-qm", "Change start script")

                report = json.loads(execute(["666DEV", project_id, "IMPACT"]))
                self.assertEqual(base, report["base"])
                checks = {item["path"]: item for item in report["checks"]}
                self.assertEqual("RECHECK", checks["tests/test_demo_app.py"]["disposition"])
                self.assertIn(["src/demo_app/main.py", "tests/test_demo_app.py"],
                              checks["tests/test_demo_app.py"]["chains"])
                self.assertEqual("UNIMPACTED", checks["tests/test_package_identity.py"]["disposition"])
                self.assertEqual([], report["fallback_reasons"])

                project = next(item for item in core.dashboard_data()["projects"] if item["id"] == project_id)
                self.assertEqual(report, project["impact"])
                checked = next(item for item in verifier.verify(base)["project_impacts"]
                               if item["project_id"] == project_id)
                self.assertEqual(report, checked)

                (app / "unknown.txt").write_text("undeclared project input", encoding="utf-8")
                fallback = json.loads(execute(["666DEV", project_id, "IMPACT"]))
                self.assertTrue(fallback["fallback_reasons"])
                self.assertTrue(all(check["disposition"] == "RECHECK" for check in fallback["checks"]))
