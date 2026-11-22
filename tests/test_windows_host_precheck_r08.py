"""Host precheck never claims Windows acceptance in CI or without evidence."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("windows_precheck", ROOT / "windows-app" / "HOST_ACCEPTANCE_R08.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class WindowsHostPrecheckTests(unittest.TestCase):
    def test_bad_sha_rejected_without_execution(self):
        with self.assertRaises(ValueError):
            module.check_host(expected_sha="HEAD")
        with self.assertRaises(ValueError):
            module.check_host(expected_sha="a" * 39)

    def test_no_ci_claim_of_windows_or_plugin_host(self):
        if os.name == "nt":
            self.skipTest("Windows test requires actual host and expected checkout")
        result = module.check_host(expected_sha="a" * 40)
        self.assertEqual("PARTIAL", result["status"])
        self.assertEqual("OFFEN", result["windows_gui_acceptance"])
        self.assertEqual("OFFEN", result["plugin_host_acceptance"])
        self.assertFalse(result["current_updated"])
        self.assertEqual(0, result["additional_cost_eur"])

    def test_launch_path_is_not_checked_without_windows(self):
        if os.name == "nt":
            self.skipTest("Only verifies non-Windows fail-closed behavior")
        with patch.object(module, "run_command") as execute:
            module.check_host(expected_sha="b" * 40)
            execute.assert_not_called()

    def test_batch_is_local_only_and_accepts_exact_sha(self):
        cmd = (ROOT / "windows-app" / "WINDOWS_HOST_PRECHECK_R08.cmd").read_text(encoding="utf-8")
        self.assertIn("HOST_ACCEPTANCE_R08.py", cmd)
        self.assertIn("--expected-sha", cmd)
        self.assertNotIn("pip install", cmd)
        self.assertNotIn("gh api", cmd)


if __name__ == "__main__":
    unittest.main()
