"""Regressions for the user-requested daily 09:00 / ten-story policy."""
import copy
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import curated_report as c
from report_timing import KST, REPORT_HOURS_KST, require_report_slot, hourly_key
from test_curated_report import NOW, HOUR, HOUR_TEXT, pick, edition, EMPTY

class DailyMorningPolicyTests(unittest.TestCase):
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
    def test_only_requested_0900_daily_slot_is_regular(self):
        self.assertEqual(REPORT_HOURS_KST,(9,))
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
        value,target=self.reviewed(age=24*3600+(NOW-HOUR)+1)
        with self.assertRaisesRegex(ValueError,"too old"):
            c.validate_edition(value,target,NOW)
        value["picks"][0]["published_at"]=None
        with self.assertRaisesRegex(ValueError,"first-publication"):
            c.validate_edition(value,target,NOW)
    def test_daily_report_includes_yesterday_daytime_and_overnight_but_not_older_news(self):
        now=int(datetime(2026,11,20,9,2,tzinfo=KST).timestamp())
        for age in (6*3600+1,12*3600+1,23*3600,24*3600):
            value,target=self.reviewed(now,age)
            self.assertEqual(len(c.validate_edition(value,target,now)["picks"]),10)
        value,target=self.reviewed(now,24*3600+121)
        with self.assertRaisesRegex(ValueError,"too old"): c.validate_edition(value,target,now)

    def test_preparation_crosses_utc_midnight_into_same_korean_morning(self):
        from report_timing import editorial_target, prepared_target
        now=int(datetime(2026,11,20,8,55,tzinfo=KST).timestamp())
        target=int(datetime(2026,11,20,9,tzinfo=KST).timestamp())
        self.assertEqual(editorial_target(now),target)
        self.assertEqual(hourly_key(target),"hourly-2026112000")
        self.assertEqual(prepared_target("2026112000",now),target)

    def test_server_refuses_to_wait_more_than_five_minutes(self):
        with patch.object(c.time,"time",return_value=NOW), patch.object(c,"prepared_target",return_value=NOW+301), \
                patch.dict("os.environ",{"BTP_MAX_PREHOUR_WAIT_SECONDS":"300"}), \
                patch.object(c,"TelegramClient") as client, patch.object(c,"wait_for_target") as wait:
            self.assertEqual(c.main(prepared_hour=HOUR_TEXT),2)
            client.assert_not_called()
            wait.assert_not_called()
