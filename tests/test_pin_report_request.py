import hashlib
import json
import unittest
from pin_report_request import bind, REQUEST, PICKS
from edition_preflight import REPORT_PICKS

class CommitBindingTests(unittest.TestCase):
    def setUp(self):
        self.approval = {"version":4,"hour_utc":"2026111009","binding":"trigger_commit"}
        self.edition = {"version":2,"hour_utc":"2026111009","reviewer":"ChatGPT","picks":[{"title":"한글"}]*REPORT_PICKS}
        self.raw = (json.dumps(self.edition, ensure_ascii=False, indent=2)+"\n").encode()
    def test_hash_uses_exact_approved_utf8_bytes(self):
        result = bind(self.approval,self.raw,[REQUEST,PICKS])
        self.assertEqual(result,{"version":2,"hour_utc":"2026111009","editorial_sha256":hashlib.sha256(self.raw).hexdigest()})
        different=self.raw.rstrip()
        self.assertNotEqual(bind(self.approval,different,[REQUEST,PICKS])["editorial_sha256"],result["editorial_sha256"])
    def test_cannot_approve_existing_or_different_edition(self):
        for paths in ([REQUEST],[PICKS],[]):
            with self.assertRaises(ValueError): bind(self.approval,self.raw,paths)
        for change in ({"hour_utc":"2026111008"},{"reviewer":"collector"},{"picks":[{}]*4},{"version":1}):
            with self.assertRaises(ValueError): bind(self.approval,json.dumps({**self.edition,**change}).encode(),[REQUEST,PICKS])
    def test_unknown_fields_and_binding_are_rejected(self):
        for approval in ({**self.approval,"binding":"main"},{**self.approval,"extra":1},{**self.approval,"hour_utc":"bad"}):
            with self.assertRaises(ValueError): bind(approval,self.raw,[REQUEST,PICKS])
    def test_existing_digest_requests_are_never_repaired(self):
        for version in (2,3):
            original={"version":version,"hour_utc":"2026111009","editorial_sha256":"0"*64}
            self.assertIs(bind(original,self.raw,[]),original)

class ImmutableCommitTests(unittest.TestCase):
    def test_pin_ignores_later_worktree_changes_and_keeps_old_digest_rejection(self):
        import subprocess
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from pin_report_request import pin
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            root=Path(directory)
            (root/"data").mkdir()
            request={"version":4,"hour_utc":"2026111009","binding":"trigger_commit"}
            raw=json.dumps({"version":2,"hour_utc":"2026111009","reviewer":"ChatGPT","picks":[{}]*REPORT_PICKS}).encode()
            (root/REQUEST).write_text(json.dumps(request))
            (root/PICKS).write_bytes(raw)
            def git(*args):
                return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL)
            git("init")
            git("config","user.name","binding-test")
            git("config","user.email","binding-test@example.invalid")
            (root/"seed").write_text("initial")
            git("add","seed")
            git("commit","-m","seed")
            git("add",REQUEST,PICKS)
            git("commit","-m","approve exact edition")
            commit=git("rev-parse","HEAD").decode().strip()
            (root/PICKS).write_bytes(b"unapproved later mutation")
            actual_check_output=subprocess.check_output
            def in_repo(args):
                return actual_check_output(args,cwd=root)
            with patch("pin_report_request.subprocess.check_output",side_effect=in_repo):
                pin(commit,root/"request-out",root/"picks-out")
            self.assertEqual((root/"picks-out").read_bytes(),raw)
            self.assertEqual(json.loads((root/"request-out").read_bytes())["editorial_sha256"],hashlib.sha256(raw).hexdigest())
            with self.assertRaises(ValueError): pin("main",root/"request-out",root/"picks-out")
