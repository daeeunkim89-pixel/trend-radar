"""Regressions for the user-requested 3-hour / ten-story policy."""
import copy
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import curated_report as c
from report_timing import KST, REPORT_HOURS_KST, require_report_slot, hourly_key
from test_curated_report import NOW, HOUR, HOUR_TEXT, pick, edition, EMPTY

class ThreeHourPolicyTests(unittest.TestCase):
    def reviewed(self, at=NOW, age=0, count=10):
        target=at//3600*3600
        picks=[pick(i) for i in range(count)]
        for p in picks:
            p.update(verified_at=at,published_at=at-age)
            p["readiness"]={"mode":"major_news","event_date":datetime.fromtimestamp(at,KST).date().isoformat(),
                            "observation":"확정 발표와 실제 영향을 원문에서 확인했다.","checked_materials":[],
                            "outline":["핵심 새 사실","한국 독자에게 중요한 변화"]}
        value=edition(picks,hour=hourly_key(target)[7:])
        value.update(version=2,generated_at=at)
        return value,target
    def test_only_five_requested_daily_slots_are_regular(self):
        self.assertEqual(REPORT_HOURS_KST,(8,11,14,17,20))
        for hour in range(24):
            target=int(datetime(2026,11,12,hour,tzinfo=KST).timestamp())
            if hour in REPORT_HOURS_KST: self.assertEqual(require_report_slot(target),target)
            else:
                with self.assertRaises(ValueError): require_report_slot(target)
    def test_ten_fit_one_message_with_original_publication_and_unique_sources(self):
        value,target=self.reviewed()
        checked=c.validate_edition(value,target,NOW)
        stories,_=c.build_stories(checked,copy.deepcopy(EMPTY),NOW)
        parts=c.render_edition(stories,target,"")
        self.assertEqual(len(parts),1)
        self.assertIn("추천 10/10",parts[0])
        self.assertEqual(parts[0].count("최초 공개"),10)
        for p in value["picks"]: self.assertIn(p["url"],parts[0])
    def test_rechecking_an_old_article_does_not_make_it_fresh(self):
        value,target=self.reviewed(age=6*3600+1)
        with self.assertRaisesRegex(ValueError,"too old"):
            c.validate_edition(value,target,NOW)
        value["picks"][0]["published_at"]=None
        with self.assertRaisesRegex(ValueError,"first-publication"):
            c.validate_edition(value,target,NOW)
    def test_morning_covers_overnight_but_not_yesterday_early_evening(self):
        now=int(datetime(2026,11,12,8,2,tzinfo=KST).timestamp())
        value,target=self.reviewed(now,11*3600)
        self.assertEqual(len(c.validate_edition(value,target,now)["picks"]),10)
        value,target=self.reviewed(now,12*3600+1)
        with self.assertRaisesRegex(ValueError,"too old"): c.validate_edition(value,target,now)
    def test_server_refuses_to_wait_more_than_five_minutes(self):
        with patch.object(c.time,"time",return_value=NOW), patch.object(c,"prepared_target",return_value=NOW+301), \
                patch.dict("os.environ",{"BTP_MAX_PREHOUR_WAIT_SECONDS":"300"}), \
                patch.object(c,"TelegramClient") as client, patch.object(c,"wait_for_target") as wait:
            self.assertEqual(c.main(prepared_hour=HOUR_TEXT),2)
            client.assert_not_called()
            wait.assert_not_called()
