"""Bounded logged-out Instagram HTML observation. No cookies, auth or private API."""
import argparse
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

PROFILE="https://www.instagram.com/bythepulse/"
EMBED=PROFILE+"embed/"
POST=re.compile(r"/(?:bythepulse/)?(?:p|reel)/([A-Za-z0-9_-]+)/?")


class Visible(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta={};self.posts=[];self.title=[];self.text=[];self.times=[]
        self.in_title=False;self.skip=0;self.caption_depth=0;self.depth=0;self.caption=[]
        self.owner_verified=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag in ("script","style"): self.skip+=1
        if tag=="title": self.in_title=True
        if tag=="meta" and (a.get("property","").startswith("og:") or a.get("property")=="article:published_time"):
            self.meta[a["property"]]=a.get("content","")[:600]
        if tag=="time" and a.get("datetime"): self.times.append(a["datetime"])
        if tag=="a":
            url=urljoin(PROFILE,a.get("href",""));p=urlsplit(url)
            match=POST.fullmatch(p.path)
            if p.hostname in ("www.instagram.com","instagram.com") and match:
                self.posts.append("https://www.instagram.com/p/"+match[1]+"/")
            if (p.hostname in ("www.instagram.com","instagram.com") and p.path.rstrip("/")=="/bythepulse"
                    and "author" in a.get("class","").lower()):
                self.owner_verified=True
        if tag not in ("meta","img","br","hr","input","link","source","wbr"):
            self.depth+=1
        if "caption" in a.get("class","").lower() and not self.caption_depth:
            self.caption_depth=self.depth
    def handle_endtag(self,tag):
        if tag=="title": self.in_title=False
        if tag in ("script","style"): self.skip=max(0,self.skip-1)
        if self.caption_depth==self.depth: self.caption_depth=0
        if tag not in ("meta","img","br","hr","input","link","source","wbr"):
            self.depth=max(0,self.depth-1)
    def handle_data(self,data):
        if self.skip:return
        if self.in_title:self.title.append(data)
        if data.strip():
            self.text.append(data.strip())
            if self.caption_depth:self.caption.append(data.strip())


def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"text/html","Accept-Encoding":"identity"})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            kind=response.headers.get("Content-Type","")
            body=response.read(2_000_001)
            if len(body)>2_000_000: return {"url":url,"status":"oversize"}
            if "html" not in kind.lower(): return {"url":url,"status":"non_html"}
            parsed=Visible();parsed.feed(body.decode("utf-8","replace"))
            visible=" ".join(parsed.text)
            barrier=bool(re.search(r"captcha|datadome|challenge|device check", " ".join(parsed.title)+" "+response.url, re.I))
            return {"url":url,"final_url":response.url,"http_status":response.status,
                    "status":"challenge" if barrier else "html_received",
                    "title":" ".join(parsed.title)[:160],"public_meta":parsed.meta,
                    "post_links":list(dict.fromkeys(parsed.posts))[:30],
                    "public_caption_excerpt":" ".join(parsed.caption)[:600],
                    "visible_excerpt":visible[:600],
                    "published_time_text":parsed.times[0] if parsed.times else None,
                    "owner_verified":parsed.owner_verified}
    except urllib.error.HTTPError as error:
        return {"url":url,"http_status":error.code,"status":"http_error"}
    except (OSError,ValueError) as error:
        return {"url":url,"status":"fetch_error","error":type(error).__name__,"detail":str(error)[:160]}


def probe(fetcher=fetch, now=None):
    now=int(time.time() if now is None else now)
    checks=[];links=[];posts=[]
    for url in (PROFILE,EMBED):
        result=fetcher(url);checks.append(result)
        if result.get("status")=="challenge" or result.get("http_status") in (401,403,429):
            break
        links=list(dict.fromkeys(links+result.get("post_links",[])))
        if links:break
    for url in links[:6]:
        result=fetcher(url+"embed/captioned/");posts.append(result)
        if result.get("status")=="challenge" or result.get("http_status") in (401,403,429):
            break
    readable=[p for p in posts if p.get("owner_verified") and p.get("public_caption_excerpt")]
    return {"version":1,"checked_at":now,"profile_url":PROFILE,
            "status":"captions_observed" if readable else "links_observed" if links else "unavailable",
            "checks":checks,"post_links":links,"posts":posts,
            "limits":["Only public HTML; no cookies, login, private API or challenge bypass.",
                      "No new posts or publication rate claimed unless actual content is returned.",
                      "Missing timestamps remain unknown; profile links alone do not establish adoption."]}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("data/btp-instagram-access.json"))
    args=parser.parse_args()
    out=probe()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"checks":[{k:v for k,v in c.items() if k in ("url","status","http_status","title","error","detail")} for c in out["checks"]],
                      "links":len(out["post_links"]),"captions":sum(bool(p.get("owner_verified") and p.get("public_caption_excerpt")) for p in out["posts"])},ensure_ascii=False))
