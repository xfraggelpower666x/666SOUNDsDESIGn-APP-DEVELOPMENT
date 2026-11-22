"""Contract regression: zero-cost policy must survive continuation and fail closed."""
import unittest

from devhub.intelligence.cost_guard import (
    BLOCK, EVENTS, evaluate, event_notice, policy_snapshot,
)


class CostConsentGuardTests(unittest.TestCase):
    def test_policy_is_zero_cost_default(self):
        policy = policy_snapshot()
        self.assertEqual(0, policy["default_budget_eur"])
        self.assertFalse(policy["auto_top_up"])
        self.assertFalse(policy["approval_reuse"])
        self.assertFalse(policy["approvals_are_portable"])

    def test_every_required_event_fails_closed_without_proof(self):
        for event in EVENTS:
            with self.subTest(event=event):
                result = event_notice(event)
                self.assertFalse(result["guard"]["allowed"])
                self.assertEqual(BLOCK, result["guard"]["status"])

    def test_free_tier_name_is_not_evidence(self):
        result = evaluate("PLUGIN_CALL", "VERIFIED_FREE")
        self.assertEqual(BLOCK, result["status"])

    def test_verified_zero_cost_with_provenance(self):
        result = evaluate("CLOUDFLARE_CHANGE", "VERIFIED_FREE",
                          evidence={"verified_zero_cost": True,
                                    "source": "provider documented free-tier limits for this operation"})
        self.assertTrue(result["allowed"])
        self.assertEqual("VERIFIZIERT", result["status"])

    def test_wallet_credit_not_free(self):
        result = evaluate("AUTOMATION", "USES_PAID_CREDITS",
                          evidence={"verified_zero_cost": True, "source": "wallet has credits"})
        self.assertFalse(result["allowed"])

    def test_unknown_cost_even_with_approval_is_blocked(self):
        result = evaluate("DEPLOY", "UNKNOWN",
                          approval={"explicit": True, "event": "DEPLOY",
                                    "action_id": "deployment-1", "max_eur": 100})
        self.assertFalse(result["allowed"])

    def test_approval_must_match_event_and_action(self):
        approval = {"explicit": True, "event": "API_CALL",
                    "action_id": "provider-123", "max_eur": 1.5}
        self.assertTrue(evaluate("API_CALL", "PAID", approval=approval)["allowed"])
        self.assertFalse(evaluate("PLUGIN_CALL", "PAID", approval=approval)["allowed"])

    def test_bad_approvals_fail_closed(self):
        for limit in (None, -1, True, "1", float("inf")):
            with self.subTest(limit=limit):
                approval = {"explicit": True, "event": "API_CALL",
                            "action_id": "provider-123", "max_eur": limit}
                self.assertFalse(evaluate("API_CALL", "PAID", approval=approval)["allowed"])

    def test_no_persisted_approval_in_snapshot_or_event(self):
        text = str(policy_snapshot()) + str(event_notice("NEXT-CHAT"))
        self.assertNotIn("provider-123", text)
        self.assertFalse(event_notice("NEW-CHAT")["guard"]["allowed"])

    def test_invalid_event_and_cost_class_rejected(self):
        for event, cost in (("FOREIGN_TRIGGER", "PAID"), ("BUILD", "FREE_MAYBE")):
            with self.assertRaises(ValueError):
                evaluate(event, cost)


if __name__ == "__main__":
    unittest.main()
