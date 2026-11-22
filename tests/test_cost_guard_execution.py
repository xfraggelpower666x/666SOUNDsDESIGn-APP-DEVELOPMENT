"""Actual executable boundary: block unverified build and start commands."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from devhub.core import run_acceptance
from devhub.intelligence.cost_guard import local_command_cost_evidence


class CostExecutionTests(unittest.TestCase):
    def run_case(self, kind, commands):
        profile = {"id": "demo-monorepo", "build_commands": commands if kind == "build" else [],
                   "start_commands": commands if kind == "start" else [],
                   "test_commands": []}
        with tempfile.TemporaryDirectory() as location:
            with patch("devhub.core.subprocess.run") as process:
                process.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
                result = run_acceptance(profile, Path(location), "f" * 40,
                                        kind=kind, source_kind="committed_copy")
                return result, process.call_count

    def test_external_build_is_denied_before_launch(self):
        result, calls = self.run_case("build", [["curl", "https://example.invalid/pay"]])
        self.assertEqual(0, calls)
        self.assertEqual("WRITE_BLOCKED", result[0]["status"])
        self.assertEqual("cost_blocked", result[0]["execution"]["state"])

    def test_start_commands_are_denied_before_launch(self):
        result, calls = self.run_case("start", [["python", "main.py"]])
        self.assertEqual(0, calls)
        self.assertEqual("WRITE_BLOCKED", result[0]["status"])

    def test_local_stdlib_compile_is_admitted(self):
        result, calls = self.run_case(
            "build", [["python", "-m", "py_compile", "src/demo_app/main.py"]])
        self.assertEqual(1, calls)
        self.assertEqual("VERIFIZIERT", result[0]["status"])

    def test_shell_or_network_build_is_not_automatically_free(self):
        for command in (["python", "-m", "pip", "install", "vendor"],
                        ["npm", "run", "build"],
                        ["python", "setup.py"],
                        ["python", "-m", "py_compile", "../escape.py"]):
            with self.subTest(command=command):
                self.assertEqual({}, local_command_cost_evidence("BUILD", command))
                result, calls = self.run_case("build", [command])
                self.assertEqual(0, calls)
                self.assertEqual("WRITE_BLOCKED", result[0]["status"])


if __name__ == "__main__":
    unittest.main()
