import copy
import unittest
from edition_preflight import preflight, validate_source_fields, SOURCE_KINDS

def edition():
    p={"title":"공식 발표로 확정된 주요 소식","category":"축구","kind":"article",
       "source":"Reuters","event_key":"confirmed-major-event","why":"리그 전체에 영향을 주는 확정 발표",
       "angle":"사실과 영향을 정리","why_now":"오늘 공식 발표","caution":"",
       "readiness":{"mode":"major_news"}}
    return {"version":2,"hour_utc":"2026111106","reviewer":"ChatGPT","picks":[copy.deepcopy(p) for _ in range(5)]}

class PreflightTests(unittest.TestCase):
    def test_real_failure_kind_major_news_is_rejected_with_location_and_fix(self):
        value=edition()
        value["picks"][3]["kind"]="major_news"
        with self.assertRaisesRegex(ValueError,r"picks\[3\].kind.*readiness.mode"): preflight(value)
    def test_major_news_mode_keeps_all_actual_source_kinds(self):
        for kind in SOURCE_KINDS:
            value=edition()
            for p in value["picks"]: p["kind"]=kind
            self.assertEqual(preflight(value),5)
    def test_validation_never_mutates_evidence_or_review_timestamps(self):
        value=edition()
        value["picks"][0]["verified_at"]=12345
        before=copy.deepcopy(value)
        preflight(value)
        self.assertEqual(value,before)
    def test_invalid_count_oversize_or_missing_kind_cannot_pass(self):
        value=edition()
        for variant in ({**value,"picks":value["picks"][:4]},
                        {**value,"version":True}):
            with self.assertRaises(ValueError): preflight(variant)
        for field,new in (("kind",None),("title","x"*91),("category","경제")):
            bad=edition()
            bad["picks"][0][field]=new
            with self.assertRaises(ValueError): preflight(bad)
    def test_source_contract_preserves_entertainment_restriction(self):
        with self.assertRaisesRegex(ValueError,"Entertainment"):
            validate_source_fields({"category":"아이돌","kind":"article"},2)
        validate_source_fields({"category":"아이돌","kind":"article"},1)
