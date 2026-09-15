import json, os, re, time, hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

STATE=Path('data/state.json'); STATE.parent.mkdir(exist_ok=True)
UA={'User-Agent':'Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/140 Safari/537.36'}
SOURCES={
 '네이버 뉴스':'https://news.naver.com/main/ranking/popularDay.naver',
 '네이버 스포츠':'https://sports.naver.com/',
 '디시 실베':'https://gall.dcinside.com/board/lists/?id=dcbest',
 '펨코 포텐':'https://www.fmkorea.com/best',
}

def num(s):
    if not s:return None
    m=re.search(r'([\d,.]+)\s*(만|천)?',s.replace(',',''))
    if not m:return None
    try:n=float(m.group(1))
    except:return None
    return int(n*(10000 if m.group(2)=='만' else 1000 if m.group(2)=='천' else 1))

def soup(url):
    r=requests.get(url,headers=UA,timeout=20); r.raise_for_status(); return BeautifulSoup(r.text,'lxml')

def item(source,title,url,views=None,reactions=None,rank=None):
    key=hashlib.sha1(url.encode()).hexdigest()[:16]
    return {'source':source,'id':key,'title':title[:180],'url':url,'views':views,'reactions':reactions,'rank':rank}

def dc():
    base=SOURCES['디시 실베']; s=soup(base); out=[]
    for rank,tr in enumerate(s.select('tr.ub-content'),1):
        a=tr.select_one('td.gall_tit a[href]')
        if not a:continue
        v=tr.select_one('td.gall_count'); r=tr.select_one('td.gall_recommend')
        out.append(item('디시 실베',' '.join(a.stripped_strings),urljoin(base,a['href']),num(v.get_text(' ',strip=True)) if v else None,num(r.get_text(' ',strip=True)) if r else None,rank))
    return out

def generic(name,allow):
    base=SOURCES[name]; s=soup(base); out=[]; seen=set()
    for a in s.select('a[href]'):
        title=' '.join(a.stripped_strings).strip(); url=urljoin(base,a.get('href',''))
        if len(title)<8 or not allow(url) or url in seen:continue
        seen.add(url); p=a.find_parent(['li','tr','article','div']) or a.parent
        text=' '.join(p.stripped_strings) if p else title
        vm=re.search(r'(?:조회|조회수|view)\s*[:：]?\s*([\d,.]+(?:만|천)?)',text,re.I)
        rm=re.search(r'(?:추천|좋아요|공감)\s*[:：]?\s*([\d,.]+(?:만|천)?)',text,re.I)
        out.append(item(name,title,url,num(vm.group(1)) if vm else None,num(rm.group(1)) if rm else None,len(out)+1))
        if len(out)>=100:break
    return out

def fetch_all():
    fs=[
      ('네이버 뉴스',lambda:generic('네이버 뉴스',lambda u:'naver.com' in urlparse(u).netloc and ('article' in u or 'news' in u))),
      ('네이버 스포츠',lambda:generic('네이버 스포츠',lambda u:'sports' in urlparse(u).netloc and ('news' in u or 'article' in u))),
      ('디시 실베',dc),
      ('펨코 포텐',lambda:generic('펨코 포텐',lambda u:'fmkorea.com' in urlparse(u).netloc and bool(re.search(r'/\d{5,}',u)))),
    ]
    out=[]
    for name,f in fs:
        try:
            x=f(); print(name,len(x)); out+=x
        except Exception as e: print('ERROR',name,repr(e))
    return out

def telegram(msg):
    tok=os.getenv('TELEGRAM_BOT_TOKEN'); chat=os.getenv('TELEGRAM_CHAT_ID')
    if not tok or not chat:
        print(msg); return
    requests.post(f'https://api.telegram.org/bot{tok}/sendMessage',data={'chat_id':chat,'text':msg,'disable_web_page_preview':False},timeout=20).raise_for_status()

def main():
    now=int(time.time())
    try: st=json.loads(STATE.read_text(encoding='utf-8'))
    except: st={'items':{},'alerts':{}}
    current=fetch_all(); alerts=[]
    for x in current:
        k=x['source']+'|'+x['id']; old=st['items'].get(k); score=0; reasons=[]
        if old:
            mins=max((now-old.get('ts',now))/60,1)
            if x['views'] is not None and old.get('views') is not None:
                d=x['views']-old['views']; rate=d/mins
                if d>=500 and rate>=100: score+=min(55,20+rate/20); reasons.append(f'조회 +{d:,} ({rate:,.0f}/분)')
            if x['reactions'] is not None and old.get('reactions') is not None:
                d=x['reactions']-old['reactions']; rate=d/mins
                if d>=15 and rate>=3: score+=min(40,15+rate*2); reasons.append(f'반응 +{d:,} ({rate:,.1f}/분)')
            if x['rank'] and old.get('rank') and old['rank']-x['rank']>=8:
                jump=old['rank']-x['rank']; score+=min(35,10+jump); reasons.append(f"순위 {old['rank']}→{x['rank']}")
        last=st['alerts'].get(k,0)
        if score>=35 and now-last>=1800:
            alerts.append((score,x,reasons)); st['alerts'][k]=now
        st['items'][k]={**x,'ts':now}
    for score,x,reasons in sorted(alerts,reverse=True,key=lambda z:z[0])[:10]:
        level='🚨 폭발' if score>=80 else '🔥 급상승'
        telegram(f"{level} · TREND {min(100,int(score))}\n[{x['source']}]\n{x['title']}\n"+' / '.join(reasons)+f"\n{x['url']}")
    # prune state to 3 days
    st['items']={k:v for k,v in st['items'].items() if now-v.get('ts',0)<259200}
    st['alerts']={k:v for k,v in st['alerts'].items() if now-v<259200}
    STATE.write_text(json.dumps(st,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
