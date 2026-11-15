import copy
import unittest
from editorial_feedback import analyze, verified_posts, filter_already_published, PROFILE, DAY

NOW=1794748800
SENT=NOW-2*DAY
def history():
    return {"editions":[{"at":SENT,"delivery":"sent","picks":[
        {"event_key":"fact-a","title":"A major change","url":"https://example.org/a"},
        {"event_key":"fact-b","title":"B major change","url":"https://example.org/b"}]}]}
def post(key="fact-a",at=SENT+3600,scope="caption"):
    return {"account":"bythepulse","post_id":"Observed123","post_url":"https://www.instagram.com/p/Observed123/",
            "scope":scope,"observed_at":NOW,"published_at":at,
            "recommendation_matches":[{"event_key":key,"same_fact_verified":True,"evidence":"Caption states the same new decision"}]}
def coverage():
    return {"at":NOW,"profile_url":PROFILE,"status":"feed_observed","complete_feed_window":True,
            "coverage_start_at":SENT,"coverage_end_at":NOW}
class FeedbackTests(unittest.TestCase):
    def test_blocked_or_partial_access_never_yields_zero_percent(self):
        for value in ({},{"profile_checks":[{"at":NOW,"status":"unavailable"}]},
                      {"observations":[post()]}):
            out=analyze(history(),value,NOW)
            self.assertIsNone(out["summary"]["publication_match_rate"])
            self.assertGreater(out["summary"]["unassessed_matured"],0)
    def test_complete_cohort_has_explicit_denominator_not_causal_adoption(self):
        out=analyze(history(),{"observations":[post()],"profile_checks":[coverage()]},NOW)
        self.assertEqual(out["summary"]["publication_match_rate"],0.5)
        self.assertEqual(out["summary"]["rate_denominator"],2)
        self.assertIsNone(out["summary"]["direct_adoption_rate"])
        self.assertEqual(out["summary"]["not_observed_in_complete_window"],1)
    def test_a_late_recommendation_is_not_a_successful_match(self):
        out=analyze(history(),{"observations":[post(at=SENT-1)],"profile_checks":[coverage()]},NOW)
        self.assertEqual(out["summary"]["already_posted_before_send"],1)
        self.assertEqual(out["summary"]["posted_after"],0)
    def test_cover_only_unknown_time_or_unverified_name_cannot_be_adoption(self):
        for p in (post(scope="cover_only"),post(at=None)):
            out=analyze(history(),{"observations":[p]},NOW)
            self.assertEqual(out["summary"]["posted_after"],0)
            self.assertIsNone(out["summary"]["publication_match_rate"])
        p=post();p["recommendation_matches"][0]["same_fact_verified"]=False
        self.assertEqual(verified_posts({"observations":[p]},NOW),[])
    def test_uncertain_delivery_and_duplicate_fact_do_not_inflate_denominator(self):
        h=history();h["editions"]+=[copy.deepcopy(h["editions"][0])]
        h["editions"]+=[{**h["editions"][0],"delivery":"uncertain"}]
        out=analyze(h,{},NOW)
        self.assertEqual(out["summary"]["unique_recommendations"],2)
        self.assertEqual(out["summary"]["sent_rows"],4)
    def test_recent_unposted_recommendations_are_pending(self):
        h=history();h["editions"][0]["at"]=NOW-3600
        out=analyze(h,{},NOW)
        self.assertEqual(out["summary"]["pending"],2)
    def test_wrong_account_or_untrusted_url_never_blocks_a_story(self):
        for field,value in (("account","other_account"),("post_url","https://example.org/p/Observed123/")):
            p=post();p[field]=value
            self.assertEqual(verified_posts({"observations":[p]},NOW),[])
    def test_malformed_coverage_does_not_turn_unknown_into_rejection(self):
        for change in ({"complete_feed_window":False},{"coverage_start_at":SENT+1},{"status":"unavailable"}):
            check={**coverage(),**change}
            self.assertIsNone(analyze(history(),{"profile_checks":[check]},NOW)["summary"]["publication_match_rate"])

    def test_verified_already_published_fact_is_filtered_even_when_exact_post_time_unknown(self):
        from unittest.mock import patch
        stories=[{"editorial":{"event_key":"fact-a"}},{"editorial":{"event_key":"fact-b"}}]
        with patch("editorial_feedback.read_json",return_value={"observations":[post(at=None)]}):
            kept,excluded=filter_already_published(stories,NOW)
        self.assertEqual((len(kept),excluded),(1,1))
        self.assertEqual(kept[0]["editorial"]["event_key"],"fact-b")

    def test_known_feed_fact_can_be_recorded_before_a_recommendation_exists(self):
        from unittest.mock import patch
        p=post();p["fact_identities"]=p.pop("recommendation_matches")
        with patch("editorial_feedback.read_json",return_value={"observations":[p]}):
            self.assertEqual(filter_already_published([{"editorial":{"event_key":"fact-a"}}],NOW),([],1))

    def test_observed_unsent_feed_fact_counts_as_a_gap_not_zero_adoption(self):
        p=post(key="new-football-fact",at=None)
        p["fact_identities"]=p.pop("recommendation_matches")
        out=analyze(history(),{"observations":[p]},NOW)
        self.assertEqual(out["summary"]["confirmed_observed_posts"],1)
        self.assertEqual(out["summary"]["observed_posts_without_same_fact_in_sent_history"],1)
        self.assertEqual(out["summary"]["observed_posts_with_same_fact_in_sent_history"],0)
        self.assertIsNone(out["summary"]["publication_match_rate"])

    def test_same_person_different_development_does_not_create_a_match(self):
        h=history()
        h["editions"][0]["picks"][0].update(event_key="son-unity-meeting",title="Son team meeting")
        p=post(key="son-contract-report",at=None)
        p["fact_identities"]=p.pop("recommendation_matches")
        out=analyze(h,{"observations":[p]},NOW)
        self.assertEqual(out["summary"]["observed_timing_unknown"],0)
        self.assertEqual(out["summary"]["observed_posts_without_same_fact_in_sent_history"],1)
