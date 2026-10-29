#!/usr/bin/env python3
"""Discover *candidate* industrial/BBQ wood pellet companies from public news RSS.

This is NOT proof that a company uses wood pellets. No login, scraping of
marketplaces, email harvesting, or shipment verification is performed.
"""
import datetime as dt
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'data' / 'discovered_companies.json'
COUNTRIES = ['Japan', 'South Korea', 'China', 'Taiwan', 'India', 'Vietnam',
             'Thailand', 'Malaysia', 'Singapore', 'Philippines', 'Indonesia',
             'Bangladesh', 'Pakistan', 'Sri Lanka', 'Cambodia', 'Myanmar',
             'United Arab Emirates', 'Saudi Arabia', 'Turkey']
SECTORS = {
    'power_generation': '"wood pellets" biomass power plant',
    'industrial_heat': '"wood pellets" industrial boiler factory',
    'bbq_smoking': '"wood pellets" BBQ smoker grill company',
    'pellet_distribution': '"BBQ pellets" distributor wholesale',
}
ORG = re.compile(r'\b([A-Z][\w&.,-]*(?:\s+[A-Z][\w&.,-]*){0,6}\s+'
                 r'(?:Co\.,? Ltd\.?|Corporation|Corp\.?|Inc\.?|Ltd\.?|'
                 r'LLC|Pte\.? Ltd\.?|Sdn\.? Bhd\.?|PLC|JSC))\b')

def get_feed(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode(
        {'q': query, 'hl': 'en', 'gl': 'US', 'ceid': 'US:en'})
    req = urllib.request.Request(url, headers={'User-Agent': 'ExportBuyerFinder/5.2 RSS discovery'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read(1_500_000))

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    existing = {}
    try:
        old = json.loads(OUT.read_text(encoding='utf-8'))
        for record in old.get('items', []):
            if isinstance(record, dict) and record.get('company_name') and record.get('country_context'):
                existing[(record['company_name'].casefold(), record['country_context'], record.get('sector', ''))] = record
    except (OSError, ValueError, TypeError):
        pass
    errors = []
    for country in COUNTRIES:
        for sector, phrase in SECTORS.items():
            try:
                feed = get_feed(f'{phrase} "{country}"')
                for item in feed.findall('./channel/item')[:10]:
                    title = (item.findtext('title') or '').strip()
                    link = (item.findtext('link') or '').strip()
                    if not title or not link.startswith('https://'):
                        continue
                    headline = title.rsplit(' - ', 1)[0]
                    if not re.search(r'\b(?:wood pellets?|BBQ pellets?)\b', headline, re.I):
                        continue
                    for match in ORG.finditer(headline):
                        name = ' '.join(match.group(1).split()).strip(' ,.-')
                        if len(name) < 7:
                            continue
                        key = (name.casefold(), country, sector)
                        rec = existing.setdefault(key, {
                            'company_name': name, 'country_context': country,
                            'sector': sector, 'company_size': 'unknown',
                            'classification': 'unverified_news_mention',
                            'wood_pellet_use_confirmed': False,
                            'official_website': None, 'public_business_email': None,
                            'source_urls': [], 'first_seen': now})
                        if link not in rec['source_urls'] and len(rec['source_urls']) < 5:
                            rec['source_urls'].append(link)
            except (OSError, ValueError, ET.ParseError) as exc:
                errors.append(f'{country}/{sector}: {type(exc).__name__}')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    items = sorted(existing.values(), key=lambda r: (r['country_context'], r['company_name']))[:1000]
    OUT.write_text(json.dumps({
        'updated_at': now, 'source': 'Google News public RSS',
        'disclaimer': 'Unverified company mentions only. Country is search context, not confirmed headquarters. Large scale and pellet use are NOT verified.',
        'items': items, 'errors': errors[:30]
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Discovered {len(items)} candidate records; {len(errors)} feed errors')

if __name__ == '__main__':
    main()
