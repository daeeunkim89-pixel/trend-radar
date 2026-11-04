import copy
import json
import os
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

import curated_report as c
import report_request
from test_curated_report import EMPTY, HOUR_TEXT, NOW, edition, pick

class SingleRequestedStoryTests(unittest.TestCase):
    def execute(self, duplicate=False, manual=True):
        value = edition([pick(1)])
        client = Mock()
        private = Mock(data={"reports": {}})
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {"BTP_REQUIRE_COMPLETE": "1"}))
            for name, value_mock in (("previous_decision", None), ("load_edition", value),
                                     ("load_history", copy.deepcopy(EMPTY)),
                                     ("TelegramClient", client), ("PrivateState", private),
                                     ("wait_for_target", True), ("deliver_report", 1)):
                stack.enter_context(patch.object(c, name, return_value=value_mock))
            stack.enter_context(patch.object(c.time, "time", return_value=NOW))
            stack.enter_context(patch.object(c, "unreported_stories", side_effect=lambda stories, *args: [] if duplicate else stories))
            write = stack.enter_context(patch.object(c, "atomic_json"))
            decision = stack.enter_context(patch.object(c, "record_decision"))
            result = c.main(recover_hour=HOUR_TEXT, user_requested=manual,
                            expected_sha256="a"*64, requested_stories=1)
        return result, client, private, write, decision

    def test_explicit_single_story_completes_one_and_keeps_hourly_target_five(self):
        result, client, private, write, decision = self.execute()
        self.assertEqual(result, 0)
        report = next(call.args[1]["report"] for call in write.call_args_list if call.args[0] == c.STATE_FILE)
        self.assertEqual((report["stories"], report["requested_stories"], report["missing"]), (1, 1, 0))
        self.assertTrue(report["target_met"])
        self.assertEqual(c.REPORT_PICKS, 5)
        stories, _ = c.build_stories(edition([pick(1)]), EMPTY, NOW)
        self.assertIn("추천 1/1", c.render_edition(stories, NOW, "", required=1)[0])

    def test_private_duplicate_still_holds_single_story_without_delivery_lock(self):
        result, client, private, write, decision = self.execute(duplicate=True)
        self.assertEqual(result, 3)
        self.assertEqual(private.data["reports"], {})
        decision.assert_not_called()
        status = next(call.args[1] for call in write.call_args_list if call.args[0] == c.ATTEMPT_FILE)
        self.assertEqual((status["ready"], status["required"], status["missing"]), (0, 1, 1))

    def test_regular_request_cannot_lower_required_count(self):
        result, client, private, write, decision = self.execute(manual=False)
        self.assertEqual(result, 1)
        client.verify.assert_not_called()
        decision.assert_not_called()
