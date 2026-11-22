"""Integration guardrails for CLI and Operations Center."""
import json
import unittest

from devhub.cli import execute
from devhub.intelligence.operations import build_operations_center


class CostGuardIntegrationTests(unittest.TestCase):
    def test_global_cost_policy_no_project_needed(self):
        policy = json.loads(execute(["666DEV", "COST-POLICY"]))
        self.assertEqual("666DEV", policy["authority"])
        self.assertEqual(0, policy["default_budget_eur"])

    def test_cli_external_call_without_evidence_is_blocked(self):
        check = json.loads(execute(["666DEV", "COST-CHECK", "PLUGIN_CALL", "PAID"]))
        self.assertFalse(check["allowed"])
        self.assertEqual("WRITE_BLOCKED", check["status"])

    def test_operations_center_rehydrates_guard_without_project(self):
        view = build_operations_center(registry={})
        self.assertEqual("REHYDRATE", view["cost_consent"]["event"])
        self.assertFalse(view["cost_consent"]["guard"]["allowed"])
        self.assertEqual(0, view["cost_consent"]["policy"]["default_budget_eur"])


if __name__ == "__main__":
    unittest.main()
