import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub import core
from devhub.cli import execute
from devhub.livecircle import resume, snapshot


class LiveCircleTests(unittest.TestCase):
    def test_native_snapshot_and_read_only_handoff(self):
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
            with patch.multiple(core, ROOT=root, REGISTRY=root / "registry" / "projects.json",
                                WORK=root / ".work"):
                project = "demo-monorepo"
                self.assertEqual("READBACK_PENDING", snapshot("demo-linked")["status"])
                self.assertEqual("OFFEN", snapshot(project)["status"])
                boot = json.loads(execute(["666DEV", "SYSTEMSTART"]))
                self.assertIn(project, boot["projects"])
                self.assertIsNone(boot["project_id"])
                self.assertEqual("PROJECT_SELECTION_REQUIRED",
                                 json.loads(execute(["666DEV", "UPDATE"]))["status"])
                self.assertEqual("READBACK_PENDING",
                                 json.loads(execute(["666DEV", "FUCK", "HORST"]))["status"])
                self.assertEqual("OFFEN", snapshot(project)["status"])
                execute(["666DEV", project, "SYSTEMSTART"])
                handoff = json.loads(execute(["666DEV", project, "NEW-CHAT"]))
                self.assertEqual("VERIFIZIERT", handoff["status"])
                self.assertEqual("WEITER", handoff["next_action"])
                self.assertIsNone(handoff["current"])
                self.assertNotIn(str(root), json.dumps(handoff))
                handoff["next_action"] = "UPDATE"
                file = root / "handoff.json"
                file.write_text(json.dumps(handoff), encoding="utf-8-sig")
                result = json.loads(execute(["666DEV", project, "NEXT-CHAT", str(file)]))
                self.assertEqual("VERIFIZIERT", result["status"])
                self.assertEqual("WEITER", result["livecircle"]["next_action"])
                self.assertEqual("CONFLICT_QUARANTINE", resume("demo-linked", handoff)["status"])
                self.assertEqual("NO_DRIFT_EVIDENCE",
                                 json.loads(execute(["666DEV", project, "FUCK", "HORST", str(file)]))["status"])
                foreign = {**handoff, "project_id": "demo-linked"}
                file.write_text(json.dumps(foreign), encoding="utf-8")
                self.assertEqual("OBSERVED_DRIFT",
                                 json.loads(execute(["666DEV", project, "FUCK", "HORST", str(file)]))["status"])
                self.assertIsNone(snapshot(project)["current"])
                execute(["666DEV", project, "SYSTEMSTART"])
                self.assertIn("working", resume(project, handoff)["changed_fields"])
                self.assertEqual("PARTIAL", resume(project, handoff)["status"])
                file.write_text(json.dumps(handoff), encoding="utf-8")
                diagnosis = json.loads(execute(["666DEV", project, "FUCK", "HORST", str(file)]))
                self.assertEqual("SUSPECTED_DRIFT", diagnosis["status"])
                self.assertIn("working", diagnosis["changed_fields"])

                app = root / "projects" / project / "app"
                (app / "dirty.txt").write_text("new local input", encoding="utf-8")
                dirty = snapshot(project)
                self.assertEqual("PARTIAL", dirty["status"])
                self.assertIsNone(dirty["next_action"])

                _, project_dir = core.project_profile(project)
                core.state_file(project_dir, "working.json").write_text("{}", encoding="utf-8")
                self.assertEqual("CONFLICT_QUARANTINE", snapshot(project)["status"])
