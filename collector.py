#!/usr/bin/env python3
"""Collect public news leads, NOT verified importers or shipments. Stdlib only."""
import datetime as dt, json, pathlib, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'data'/'signals.json'
COUNTRIES=['Japan','South Korea','China','India','Vietnam','Thailand','Malaysia','Singapore','Philippines','Taiwan','Bangladesh','Pakistan','Sri Lanka','Myanmar','Cambodia','Laos','Brunei','Mongolia','Kazakhstan','Uzbekistan','Turkey','United Arab Emirates','Saudi Arabia','Qatar','Oman','Kuwait','Bahrain','Jordan','Nepal','Indonesia']
QUERIES=['"wood pellets" import {country}','"wood pellet" procurement {country}']

def fetch(q):
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':q,'hl':'en','gl':'US','ceid':'US:en'})
    req=urllib.request.Request(url,headers={'User-Agent':'ExportBuyerFinder/1.1 (+public RSS reader)'})
    with urllib.request.urlopen(req,timeout=20) as resp:
        return ET.fromstring(resp.read(1_500_000))

def main():
    old=[]
    if OUT.exists():
        try: old=json.loads(OUT.read_text()).get('items',[])
        except (ValueError, OSError): pass
    found={i['url']:i for i in old if isinstance(i,dict) and i.get('url')}
    errors=[]
    for country in COUNTRIES:
        for template in QUERIES:
            q=template.format(country=country)
            try:
                root=fetch(q)
                for item in root.findall('./channel/item')[:8]:
                    title=(item.findtext('title') or '').strip()
                    link=(item.findtext('link') or '').strip()
                    if not title or not link.startswith('https://'): continue
                    published=(item.findtext('pubDate') or '').strip()
                    try: iso=parsedate_to_datetime(published).astimezone(dt.timezone.utc).isoformat()
                    except (ValueError, TypeError): iso=''
                    found[link]={'title':title[:300],'url':link,'country':country,'published':iso,'query':q,'classification':'unverified_news_signal'}
            except (OSError, ET.ParseError, ValueError) as exc: errors.append(f'{country}: {type(exc).__name__}')
    items=sorted(found.values(),key=lambda x:x.get('published',''),reverse=True)[:500]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'Google News public RSS','disclaimer':'News signals only. No importer, shipment, or email verification.','items':items,'errors':errors[:20]},ensure_ascii=False,indent=2)+'\n')
    print(f'Saved {len(items)} signals; {len(errors)} feed errors')

if __name__=='__main__': main()
