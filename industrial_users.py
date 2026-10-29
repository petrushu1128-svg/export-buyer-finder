#!/usr/bin/env python3
"""Build multi-sector wood-pellet prospect database from reviewed seed entries.
Does NOT discover new companies or verify active purchasing.
"""
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SEED = ROOT / 'data' / 'industrial_seed.json'
OUTPUT = ROOT / 'data' / 'industrial_users.json'
SECTORS = {'power_generation', 'industrial_boiler', 'bbq_grill_manufacturer',
           'bbq_fuel_distributor', 'industrial_food_smoking', 'other_verified_pellet_use'}
ROLES = {'end_user', 'plant_operator', 'fuel_supplier', 'investor',
         'manufacturer', 'distributor', 'unknown'}
EVIDENCE = {'official_company_source', 'official_project_source', 'public_document',
            'third_party_report', 'unreviewed'}

def valid_url(value):
    return isinstance(value, str) and urlparse(value).scheme == 'https' and bool(urlparse(value).netloc)

def main():
    seed = json.loads(SEED.read_text(encoding='utf-8'))
    if not isinstance(seed, list):
        raise ValueError('Seed must be a JSON list')
    records = []
    seen = set()
    for index, item in enumerate(seed, 1):
        if not isinstance(item, dict):
            raise ValueError(f'Record {index} must be an object')
        for key in ('company_name', 'country', 'facility_name', 'role', 'sector', 'evidence_url', 'evidence_type'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'Record {index}: missing {key}')
        if item['sector'] not in SECTORS or item['role'] not in ROLES or item['evidence_type'] not in EVIDENCE:
            raise ValueError(f'Record {index}: invalid sector, role or evidence_type')
        if not valid_url(item['evidence_url']):
            raise ValueError(f'Record {index}: evidence_url must be HTTPS')
        if item.get('official_website') and not valid_url(item['official_website']):
            raise ValueError(f'Record {index}: official_website must be HTTPS')
        key = (item['company_name'].casefold(), item['country'].casefold(), item['facility_name'].casefold(), item['sector'])
        if key in seen:
            continue
        seen.add(key)
        record = dict(item)
        record['verification_status'] = 'needs_manual_review'
        record['active_purchase_confirmed'] = False
        records.append(record)
    records.sort(key=lambda r: (r['country'], r['sector'], r['company_name'], r['facility_name']))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        'updated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'method': 'curated_seed_only',
        'disclaimer': 'Prospects are not verified importers or active buyers. Review sources and pellet grade before outreach.',
        'items': records
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Generated {len(records)} multi-sector prospects')

if __name__ == '__main__':
    main()
