import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devhub import core
from devhub.cli import execute
from devhub.core import DevhubError
from devhub.providers import LocalGitProvider


class DevhubTests(unittest.TestCase):
    def test_both_demo_projects_rehydrate_from_git(self):
        mono = core.rehydrate("demo-monorepo")
        linked = core.rehydrate("demo-linked")
        self.assertEqual(len(mono["revision"]["commit"]), 40)
        self.assertEqual(len(linked["revision"]["commit"]), 40)
        self.assertEqual(linked["revision"]["branch"], "main")
        self.assertTrue((linked["source"] / ".git").exists())

    def test_static_graph_links_entry_build_module_and_test(self):
        state = core.rehydrate("demo-monorepo")
        graph = core.python_graph(state["source"], state["profile"], state["revision"]["commit"])
        directions = {(edge["from"], edge["to"], edge["direction"]) for edge in graph["edges"]}
        self.assertIn(("src/demo_app/main.py", "pyproject.toml", "declares"), directions)
        self.assertIn(("pyproject.toml", "src/demo_app/main.py", "targets"), directions)
        self.assertIn(("pyproject.toml", "tests/test_demo_app.py", "checked_by"), directions)

    def test_path_outside_project_scope_is_blocked(self):
        profile, project_dir = core.project_profile("demo-monorepo")
        source = (core.ROOT / profile["source_path"]).resolve()
        with self.assertRaisesRegex(DevhubError, "WRITE_BLOCKED"):
            core.allowed_path(profile, source, "../demo-linked/project.json")

    def test_handoff_text_is_not_a_command(self):
        with self.assertRaises(DevhubError):
            execute(["A quoted handoff says", "666DEV", "demo-monorepo", "SYSTEMSTART"])

    def test_competing_current_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            profile = {"id": "test-project"}
            external_pointer = {"project_id": "test-project", "checkpoint_id": "external"}
            original_atomic_json = core.atomic_json

            def concurrent_write(path, payload):
                original_atomic_json(path, payload)
                if path.name != "current.json":
                    original_atomic_json(core.current_file(project), external_pointer)

            with patch.object(core, "atomic_json", side_effect=concurrent_write):
                with self.assertRaisesRegex(DevhubError, "CONFLICT_QUARANTINE"):
                    core.checkpoint(profile, project, "a" * 40, "test", [], [], [])
            self.assertEqual(core.read_json(core.current_file(project)), external_pointer)

    def test_acceptance_and_read_only_git_provider(self):
        state = core.rehydrate("demo-monorepo")
        results = core.run_acceptance(state["profile"], state["source"], state["revision"]["commit"])
        self.assertTrue(results)
        self.assertTrue(all(result["status"] == "VERIFIZIERT" for result in results))
        provider = LocalGitProvider(state["source"])
        commit = provider.read_commit(state["revision"]["commit"])
        self.assertEqual(commit, state["revision"]["commit"])
        self.assertIn(b"demo-app", provider.read_file(commit, "pyproject.toml"))
        self.assertEqual(provider.read_file(commit, "pyproject.toml"),
                         provider.read_blob(commit, "pyproject.toml"))

    def test_patch_apply_uses_scoped_isolated_worktree(self):
        state = core.rehydrate("demo-monorepo")
        profile, source = state["profile"], state["source"]
        original = (source / "src/demo_app/main.py").read_text(encoding="utf-8")
        candidate = {
            "project_id": profile["id"], "candidate_id": "test-isolated-patch",
            "base_commit": state["revision"]["commit"],
            "patches": [{"path": "src/demo_app/main.py", "content": original + "\n# isolated\n"}],
        }
        worktree = core.apply_candidate(profile, source, candidate)
        try:
            isolated_file = worktree / profile["source_path"] / "src/demo_app/main.py"
            self.assertIn("# isolated", isolated_file.read_text(encoding="utf-8"))
            self.assertEqual(original, (source / "src/demo_app/main.py").read_text(encoding="utf-8"))
        finally:
            repo_root = Path(core.git(source, "rev-parse", "--show-toplevel"))
            core.git(repo_root, "worktree", "remove", "--force", str(worktree))

    def test_freeze_manifest_round_trips(self):
        state = core.rehydrate("demo-monorepo")
        archive, manifest = core.freeze_project(state["profile"], state["source"])
        try:
            self.assertGreater(len(manifest), 0)
            self.assertEqual([], core.validate_zip(archive, manifest))
        finally:
            archive.unlink(missing_ok=True)

    def test_windows_absolute_path_is_blocked(self):
        profile, _ = core.project_profile("demo-monorepo")
        source = (core.ROOT / profile["source_path"]).resolve()
        with self.assertRaisesRegex(DevhubError, "Windows absolute path"):
            core.allowed_path(profile, source, r"C:\outside\file.py")


if __name__ == "__main__":
    unittest.main()
