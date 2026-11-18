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
                update = json.loads(execute(["666DEV", "UPDATE"]))
                self.assertEqual("PROJECT_SELECTION_REQUIRED", update["status"])
                self.assertFalse(update["source_integration"]["requires_project_selection"])
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
                self.assertEqual("MATCHES_HANDOFF", result["recovery"]["context"]["state"])
                self.assertEqual(["666DEV", project, "WEITER"],
                                 result["recovery"]["project"]["native_next_command"])
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
                stale_context = resume(project, handoff)
                self.assertEqual("PARTIAL", stale_context["status"])
                self.assertEqual("REBUILD_FROM_NATIVE", stale_context["recovery"]["context"]["state"])
                self.assertNotIn("inspection_command", stale_context["recovery"]["project"])
                file.write_text(json.dumps(handoff), encoding="utf-8")
                diagnosis = json.loads(execute(["666DEV", project, "FUCK", "HORST", str(file)]))
                self.assertEqual("SUSPECTED_DRIFT", diagnosis["status"])
                self.assertIn("working", diagnosis["changed_fields"])

                app = root / "projects" / project / "app"
                (app / "dirty.txt").write_text("new local input", encoding="utf-8")
                self.assertEqual(["666DEV", project, "IMPACT"],
                                 resume(project, handoff)["recovery"]["project"]["inspection_command"])
                dirty = snapshot(project)
                self.assertEqual("PARTIAL", dirty["status"])
                self.assertIsNone(dirty["next_action"])

                core.git(root, "add", str(app / "dirty.txt"))
                core.git(root, "commit", "-qm", "Change project source")
                recovered = resume(project, handoff)
                project_recovery = recovered["recovery"]["project"]
                self.assertEqual("REVALIDATE_PROJECT", project_recovery["state"])
                self.assertEqual(["666DEV", project, "IMPACT", handoff["source_commit"]],
                                 project_recovery["inspection_command"])
                self.assertEqual("VERIFIZIERT", project_recovery["impact"]["status"])
                self.assertEqual(1, project_recovery["impact"]["changed_path_count"])
                self.assertGreater(project_recovery["impact"]["checks_to_repeat"], 0)
                unknown = resume(project, {**handoff, "source_commit": "a" * 40})
                self.assertEqual("READBACK_PENDING", unknown["recovery"]["project"]["impact"]["status"])
                self.assertEqual(["666DEV", project, "IMPACT"],
                                 unknown["recovery"]["project"]["inspection_command"])
                self.assertIsNone(snapshot(project)["current"])

                _, project_dir = core.project_profile(project)
                core.state_file(project_dir, "working.json").write_text("{}", encoding="utf-8")
                self.assertEqual("CONFLICT_QUARANTINE", snapshot(project)["status"])
