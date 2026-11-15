import unittest
from instagram_public import Visible,probe,PROFILE,EMBED
class PublicInstagramTests(unittest.TestCase):
    def test_public_links_and_visible_caption_without_script_contents(self):
        p=Visible();p.feed('<a href="/p/Verified123/">post</a><div class="Caption">Actual public caption<script>hidden script</script></div><a class="AuthorUsername" href="/bythepulse/">btp</a><time datetime="2026-11-15T12:00:00Z">time</time>')
        self.assertEqual(p.posts,["https://www.instagram.com/p/Verified123/"])
        self.assertEqual(p.caption,["Actual public caption"])
        self.assertTrue(p.owner_verified)
        self.assertEqual(p.times,["2026-11-15T12:00:00Z"])
    def test_login_page_never_becomes_a_readable_post(self):
        out=probe(lambda url:{"url":url,"status":"html_received","post_links":[],"title":"Login"},now=1)
        self.assertEqual(out["status"],"unavailable")
        self.assertEqual(out["posts"],[])
    def test_access_barrier_stops_without_embed_retry(self):
        calls=[]
        def blocked(url):
            calls.append(url);return {"url":url,"http_status":429,"status":"http_error"}
        out=probe(blocked,1)
        self.assertEqual(calls,[PROFILE])
        self.assertEqual(out["status"],"unavailable")
    def test_official_embed_fallback_and_only_observed_post_urls(self):
        calls=[]
        def public(url):
            calls.append(url)
            if url==PROFILE:return {"status":"html_received","post_links":[]}
            if url==EMBED:return {"status":"html_received","post_links":["https://www.instagram.com/p/Verified123/"]}
            return {"status":"html_received","owner_verified":True,"public_caption_excerpt":"Actual caption"}
        self.assertEqual(probe(public,1)["status"],"captions_observed")
        self.assertEqual(calls[-1],"https://www.instagram.com/p/Verified123/embed/captioned/")
