"""Production completion tests: a short edition must leave delivery unattempted."""
import copy
import os
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

import curated_report as c
from quick_scan import inbox
from test_curated_report import EMPTY, HOUR, HOUR_TEXT, NOW, edition, pick


class CompleteDeliveryTests(unittest.TestCase):
    def execute(self, count, dedup_count=None):
        value = edition([pick(i) for i in range(count)])
        client = Mock()
        private = Mock(data={"reports": {}})
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"BTP_REQUIRE_COMPLETE": "1"}))
            stack.enter_context(patch.object(c.time, "time", return_value=NOW))
            stack.enter_context(patch.object(c, "previous_decision", return_value=None))
            stack.enter_context(patch.object(c, "load_edition", return_value=value))
            stack.enter_context(patch.object(c, "load_history", return_value=copy.deepcopy(EMPTY)))
            connection = stack.enter_context(patch.object(c, "TelegramClient", return_value=client))
            stack.enter_context(patch.object(c, "PrivateState", return_value=private))
            stack.enter_context(patch.object(c, "wait_for_target", return_value=True))
            stack.enter_context(patch.object(c, "unreported_stories",
                side_effect=lambda stories, *args: stories if dedup_count is None else stories[:dedup_count]))
            write = stack.enter_context(patch.object(c, "atomic_json"))
            decision = stack.enter_context(patch.object(c, "record_decision"))
            delivery = stack.enter_context(patch.object(c, "deliver_report", return_value=1))
            result = c.main(recover_hour=HOUR_TEXT)
        return result, connection, private, write, decision, delivery

    def test_zero_or_four_requires_more_research_before_telegram_or_slot_lock(self):
        for count in (0, 4):
            with self.subTest(count=count):
                result, connection, private, write, decision, delivery = self.execute(count)
                self.assertEqual(result, 3)
                connection.assert_not_called()
                delivery.assert_not_called()
                decision.assert_not_called()
                self.assertEqual(private.data["reports"], {})
                status = next(call.args[1] for call in write.call_args_list if call.args[0] == c.ATTEMPT_FILE)
                self.assertEqual((status["status"], status["ready"], status["missing"]),
                                 ("needs_more_research", count, 5-count))

    def test_private_dedup_shortfall_does_not_send_or_lock_four(self):
        result, connection, private, write, decision, delivery = self.execute(8, 4)
        self.assertEqual(result, 3)
        delivery.assert_not_called()
        decision.assert_not_called()
        self.assertEqual(private.data["reports"], {})
        status = next(call.args[1] for call in write.call_args_list if call.args[0] == c.ATTEMPT_FILE)
        self.assertEqual((status["ready"], status["duplicates_excluded"]), (4, 4))

    def test_reviewed_reserves_complete_five_after_private_dedup(self):
        result, connection, private, write, decision, delivery = self.execute(8, 5)
        self.assertEqual(result, 0)
        delivery.assert_called_once()
        self.assertEqual(len(delivery.call_args.kwargs["numbers"]), 5)
        decision.assert_called_once()
        report = next(call.args[1]["report"] for call in write.call_args_list if call.args[0] == c.STATE_FILE)
        self.assertTrue(report["target_met"])
        self.assertEqual(report["stories"], 5)

    def test_research_has_one_extension_without_erasing_completion_checks(self):
        budget = inbox({}, NOW)["budget"]
        self.assertFalse(budget["extend_until_target"])
        self.assertEqual(budget["max_extensions"], 1)
        self.assertEqual((budget["initial_searches"], budget["extension_searches"],
                          budget["recommendations_target"]), (4, 2, 5))
        value = edition()
        value["coverage"]["queries"] = ["checked source query " + str(i) for i in range(60)]
        value["coverage"]["opened_urls"] += ["https://example.org/checked/" + str(i) for i in range(90)]
        self.assertEqual(len(c.validate_edition(value, HOUR, NOW)["coverage"]["queries"]), 60)
