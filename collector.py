#!/usr/bin/env python3
"""Collect public wood-pellet news and cautious company leads. Stdlib only.

Company names are candidate mentions, NOT verified importers.
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
SIGNALS = ROOT / 'data' / 'signals.json'
BUYERS = ROOT / 'data' / 'buyers.json'
COUNTRIES = ['Japan','South Korea','China','India','Vietnam','Thailand','Malaysia','Singapore','Philippines','Taiwan','Bangladesh','Pakistan','Sri Lanka','Myanmar','Cambodia','Laos','Brunei','Mongolia','Kazakhstan','Uzbekistan','Turkey','United Arab Emirates','Saudi Arabia','Qatar','Oman','Kuwait','Bahrain','Jordan','Nepal','Indonesia']
QUERIES = ['"wood pellets" import {country}', '"wood pellet" procurement {country}']
# Only explicit organization suffixes, and only in a headline about wood pellets.
COMPANY = re.compile(r'\b([A-Z][A-Za-z0-9&.,\-]*(?:\s+[A-Z][A-Za-z0-9&.,\-]*){0,5}\s+(?:Co\.?\s*,?\s*Ltd\.?|Company Limited|Corporation|Corp\.?|Inc\.?|Ltd\.?|LLC|Pte\.?\s+Ltd\.?|Sdn\.?\s+Bhd\.?|JSC|PLC))\b')
BLOCK = {'Wood Pellet', 'Wood Pellets', 'Google News'}

def fetch(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query, 'hl':'en', 'gl':'US', 'ceid':'US:en'})
    req = urllib.request.Request(url, headers={'User-Agent':'ExportBuyerFinder/2.0 (public RSS reader)'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read(1_500_000))

def load_items(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data.get('items', []) if isinstance(data, dict) and isinstance(data.get('items'), list) else []
    except (OSError, ValueError):
        return []

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    found = {x['url']: x for x in load_items(SIGNALS) if isinstance(x, dict) and x.get('url')}
    errors = []
    for country in COUNTRIES:
        for template in QUERIES:
            query = template.format(country=country)
            try:
                root = fetch(query)
                for item in root.findall('./channel/item')[:8]:
                    title = (item.findtext('title') or '').strip()
                    link = (item.findtext('link') or '').strip()
                    if not title or not link.startswith('https://'):
                        continue
                    raw_date = (item.findtext('pubDate') or '').strip()
                    try:
                        published = parsedate_to_datetime(raw_date).astimezone(dt.timezone.utc).isoformat()
                    except (ValueError, TypeError, OverflowError):
                        published = ''
                    found[link] = {'title':title[:300], 'url':link, 'country':country, 'published':published, 'query':query, 'classification':'unverified_news_signal'}
            except (OSError, ET.ParseError, ValueError) as exc:
                errors.append(f'{country}: {type(exc).__name__}')
    signals = sorted(found.values(), key=lambda x:x.get('published',''), reverse=True)[:500]
    save(SIGNALS, {'updated_at':now, 'source':'Google News public RSS', 'disclaimer':'News signals only. No importer, shipment, or email verification.', 'items':signals, 'errors':errors[:20]})

    buyers = {}
    for signal in signals:
        headline = signal['title'].split(' - ')[0]
        if not re.search(r'wood\s+pellets?', headline, re.I):
            continue
        for match in COMPANY.finditer(headline):
            name = re.sub(r'\s+', ' ', match.group(1)).strip(' ,.-')
            if name in BLOCK or len(name) < 7:
                continue
            key = (name.casefold(), signal['country'])
            record = buyers.setdefault(key, {'company_name':name, 'country_context':signal['country'], 'classification':'unverified_company_mention', 'official_website':None, 'public_purchasing_email':None, 'shipment_verified':False, 'shipment_evidence_url':None, 'source_urls':[]})
            if signal['url'] not in record['source_urls'] and len(record['source_urls']) < 5:
                record['source_urls'].append(signal['url'])
    rows = sorted(buyers.values(), key=lambda r:(r['country_context'],r['company_name']))
    save(BUYERS, {'updated_at':now, 'source':'Organization-like names extracted from public news headlines', 'disclaimer':'Candidates only. Country is article search context, not confirmed headquarters. No import activity, website or email verified.', 'items':rows})
    print(f'Saved {len(signals)} news signals, {len(rows)} unverified company mentions, {len(errors)} feed errors')

if __name__ == '__main__':
    main()
