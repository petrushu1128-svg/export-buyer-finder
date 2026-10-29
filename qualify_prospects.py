#!/usr/bin/env python3
"""Build a conservative review queue from existing wood pellet discovery data.
Does not infer confirmed users, purchasing intent, company size, or emails.
"""
import datetime as dt
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / 'data' / 'discovered_companies.json'
SEED = ROOT / 'data' / 'industrial_users.json'
OUTPUT = ROOT / 'data' / 'prospect_review_queue.json'

def read_items(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data.get('items', []) if isinstance(data, dict) and isinstance(data.get('items'), list) else []
    except (OSError, ValueError):
        return []

def text(value):
    return value.strip() if isinstance(value, str) else ''

def main():
    candidates = {}
    for source_name, path in [('discovery', SOURCE), ('industrial_seed', SEED)]:
        for item in read_items(path):
            if not isinstance(item, dict):
                continue
            name = text(item.get('company_name'))
            if not name:
                continue
            country = text(item.get('country')) or text(item.get('country_context')) or 'Unknown'
            key = (re.sub(r'\W+', '', name.casefold()), country.casefold())
            row = candidates.setdefault(key, {
                'company_name': name, 'country_context': country,
                'sectors': [], 'discovery_sources': [], 'evidence_urls': [],
                'official_website': None, 'public_business_email': None,
                'wood_pellet_use_confirmed': False,
                'active_purchase_confirmed': False,
                'large_company_confirmed': False,
                'review_status': 'needs_manual_evidence_review',
                'priority': 'research',
            })
            sector = text(item.get('sector'))
            if sector and sector not in row['sectors']:
                row['sectors'].append(sector)
            if source_name not in row['discovery_sources']:
                row['discovery_sources'].append(source_name)
            urls = item.get('source_urls', [])
            if not isinstance(urls, list):
                urls = []
            evidence = text(item.get('evidence_url'))
            if evidence:
                urls.append(evidence)
            for url in urls:
                if isinstance(url, str) and url.startswith('https://') and url not in row['evidence_urls']:
                    row['evidence_urls'].append(url)
            # A URL or an earlier unreviewed flag is NOT independent confirmation.
            # Preserve provided site as a lead, not as proof of company identity.
            site = text(item.get('official_website'))
            if site.startswith('https://') and not row['official_website']:
                row['official_website'] = site
            email = text(item.get('public_business_email'))
            if email and not row['public_business_email']:
                row['public_business_email'] = email
    rows = sorted(candidates.values(), key=lambda x: (x['country_context'], x['company_name']))
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        'updated_at': now,
        'disclaimer': 'Research queue only; no company size, pellet usage, active purchasing, or source validity independently verified.',
        'stats': {'unique_name_country_pairs': len(rows), 'needs_review': len(rows)},
        'items': rows
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {len(rows)} prospects for manual evidence review: {OUTPUT}')

if __name__ == '__main__':
    main()
