#!/usr/bin/env python3
"""Asia wood-pellet discovery via public Google News RSS (stdlib only).

No scraping of B2B portals, login bypass, or shipment verification.
All generated leads are unverified and require human review.
"""
import datetime as dt
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / 'data'
COUNTRIES = ['Japan','South Korea','China','India','Vietnam','Thailand','Malaysia','Singapore','Philippines','Taiwan','Bangladesh','Pakistan','Sri Lanka','Myanmar','Cambodia','Laos','Brunei','Mongolia','Kazakhstan','Uzbekistan','Turkey','United Arab Emirates','Saudi Arabia','Qatar','Oman','Kuwait','Bahrain','Jordan','Nepal','Indonesia']
# A modest number of queries to limit requests and Actions run time.
QUERIES = [
    ('rfq', '"wood pellets" "buy" {country}'),
    ('rfq', '"wood pellets" "tender" {country}'),
    ('company', '"wood pellet" "importer" {country}'),
    ('company', '"wood pellets" "power plant" {country}'),
]
ORG = re.compile(r'\b([A-Z][A-Za-z0-9&.,\-]*(?:\s+[A-Z][A-Za-z0-9&.,\-]*){0,5}\s+(?:Co\.?\s*,?\s*Ltd\.?|Company Limited|Corporation|Corp\.?|Inc\.?|Ltd\.?|LLC|Pte\.?\s+Ltd\.?|Sdn\.?\s+Bhd\.?|JSC|PLC))\b')
# Avoid promoting generic terms into company records.
BAD = re.compile(r'^(?:Wood Pellets?|Biomass|Google News|Asia|Global|The|New|South Korea|United Arab Emirates)\b', re.I)
RFQ_WORDS = re.compile(r'\b(?:buy(?:ing|ers?)?|purchase|procure(?:ment)?|rfq|tender|seeking|wanted|sourcing|supply agreement)\b', re.I)
COMPANY_WORDS = re.compile(r'\b(?:import(?:s|er|ers|ing)?|procure(?:ment)?|purchase|power plant|utility|biomass|wood pellet)\b', re.I)


def load(path):
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return obj.get('items', []) if isinstance(obj, dict) and isinstance(obj.get('items'), list) else []
    except (OSError, ValueError):
        return []


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fetch(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q':query,'hl':'en','gl':'US','ceid':'US:en'})
    req = urllib.request.Request(url, headers={'User-Agent':'ExportBuyerFinder/4.0 (public RSS; contact: repository owner)'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return ET.fromstring(resp.read(1_500_000))


def collect():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    signals = {r['url']:r for r in load(DATA/'signals.json') if isinstance(r,dict) and r.get('url')}
    rfqs = {r['source_url']:r for r in load(DATA/'rfqs.json') if isinstance(r,dict) and r.get('source_url')}
    errors = []
    for country in COUNTRIES:
        for kind, template in QUERIES:
            q = template.format(country=country)
            try:
                root = fetch(q)
                for item in root.findall('./channel/item')[:6]:
                    title = (item.findtext('title') or '').strip()
                    url = (item.findtext('link') or '').strip()
                    if not title or not url.startswith('https://'):
                        continue
                    try:
                        published = parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(dt.timezone.utc).isoformat()
                    except (ValueError, TypeError, OverflowError):
                        published = ''
                    rec = {'title':title[:300], 'url':url, 'country_context':country,
                           'published':published, 'query':q, 'classification':'unverified_news_signal'}
                    signals[url] = rec
                    if kind == 'rfq' and RFQ_WORDS.search(title) and re.search(r'wood\s+pellets?', title, re.I):
                        rfqs[url] = {'title':title[:300], 'country_context':country, 'published':published,
                                     'source_url':url, 'source_type':'news_search_result',
                                     'classification':'unverified_purchase_signal',
                                     'buyer_name':None, 'quantity_mt':None, 'contact_email':None}
            except (OSError, ET.ParseError, ValueError) as exc:
                errors.append({'country':country, 'query':q, 'error':type(exc).__name__})
    signal_rows = sorted(signals.values(),key=lambda x:x.get('published',''),reverse=True)[:800]
    rfq_rows = sorted(rfqs.values(),key=lambda x:x.get('published',''),reverse=True)[:500]
    # Preserve older buyer records, but never upgrade their verification status.
    buyers = {}
    for old in load(DATA/'buyers.json'):
        if isinstance(old,dict) and old.get('company_name'):
            buyers[(old['company_name'].casefold(),old.get('country_context',''))] = old
    for s in signal_rows:
        headline = s['title'].split(' - ')[0]
        if not COMPANY_WORDS.search(headline):
            continue
        for match in ORG.finditer(headline):
            name = re.sub(r'\s+',' ',match.group(1)).strip(' ,.-')
            if len(name)<7 or BAD.match(name):
                continue
            key=(name.casefold(),s['country_context'])
            rec=buyers.setdefault(key,{'company_name':name,'country_context':s['country_context'],
                'classification':'unverified_company_mention','official_website':None,
                'public_purchasing_email':None,'shipment_verified':False,
                'shipment_evidence_url':None,'source_urls':[]})
            if s['url'] not in rec.get('source_urls',[]) and len(rec.get('source_urls',[]))<5:
                rec.setdefault('source_urls',[]).append(s['url'])
    buyer_rows=sorted(buyers.values(),key=lambda x:(x.get('country_context',''),x.get('company_name','')))[:500]
    save(DATA/'signals.json',{'updated_at':now,'source':'Google News public RSS',
         'disclaimer':'News results are not proof of imports or buyer intent. Country is query context.',
         'items':signal_rows,'errors':errors[:30]})
    save(DATA/'rfqs.json',{'updated_at':now,'source':'Google News RSS keyword discovery',
         'disclaimer':'Purchase-related headlines only; not verified B2B RFQs, buyer identities, or quantities.',
         'items':rfq_rows})
    save(DATA/'buyers.json',{'updated_at':now,'source':'Company suffix matches in public news headlines',
         'disclaimer':'Unverified mentions, not confirmed importers or wood-pellet purchasers. Country is search context.',
         'items':buyer_rows})
    print(f'Saved {len(signal_rows)} signals, {len(rfq_rows)} purchase signals, {len(buyer_rows)} company mentions; {len(errors)} errors')

if __name__=='__main__':
    collect()
