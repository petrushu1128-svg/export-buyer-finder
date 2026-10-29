#!/usr/bin/env python3
"""Discover UNVERIFIED wood-pellet company leads from public Google News RSS.
No proof of wood-pellet use, company size, headquarters, or purchasing intent.
Python standard library only.
"""
import datetime as dt
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data" / "discovered_companies.json"
COUNTRIES = [
    "Japan", "South Korea", "China", "Taiwan", "India", "Vietnam",
    "Thailand", "Malaysia", "Singapore", "Philippines", "Indonesia",
    "Bangladesh", "Pakistan", "Sri Lanka", "Cambodia", "Myanmar",
    "United Arab Emirates", "Saudi Arabia", "Turkey"
]
SECTORS = {
    "power_generation": [
        '"wood pellet" "power plant" {country}',
        '"biomass pellets" "power station" {country}',
    ],
    "industrial_heat": [
        '"wood pellet" "industrial boiler" {country}',
        '"wood pellets" "factory" "fuel" {country}',
    ],
    "bbq_smoking": [
        '"wood pellets" "BBQ" "company" {country}',
        '"pellet grill" "smoking pellets" {country}',
    ],
    "pellet_distribution": [
        '"wood pellet" "distributor" {country}',
        '"wood pellet" "importer" {country}',
    ],
}
# Name-like phrases, not proof of legal entity or commercial activity.
ORG = re.compile(
    r"\b([A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,5}"
    r"\s+(?:Co\.,?\s*Ltd\.?|Co\.?\s*Ltd\.?|Corporation|Corp\.?|"
    r"Inc\.?|Ltd\.?|LLC|PLC|Pte\.?\s*Ltd\.?|Sdn\.?\s*Bhd\.?|JSC))\b"
)
PELLET = re.compile(r"\b(?:wood|biomass|hardwood)\s+pellets?\b", re.I)
BLOCK = re.compile(r"^(?:wood pellets?|biomass pellets?|google news)\b", re.I)

def fetch(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "en", "gl": "US", "ceid": "US:en"
    })
    req = urllib.request.Request(url, headers={
        "User-Agent": "ExportBuyerFinder/5.3 (public RSS reader)"
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        return ET.fromstring(response.read(1_500_000))

def load_existing():
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
        return data.get("items", []) if isinstance(data.get("items"), list) else []
    except (OSError, ValueError, TypeError, AttributeError):
        return []

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    existing = {}
    for rec in load_existing():
        if not isinstance(rec, dict):
            continue
        name = rec.get("company_name")
        country = rec.get("country_context")
        sector = rec.get("sector")
        if name and country and sector:
            existing[(name.casefold(), country, sector)] = rec
    errors = []
    queries_run = 0
    articles_checked = 0
    for country in COUNTRIES:
        for sector, templates in SECTORS.items():
            for template in templates:
                query = template.format(country=country)
                queries_run += 1
                try:
                    feed = fetch(query)
                    for item in feed.findall("./channel/item")[:10]:
                        articles_checked += 1
                        title = (item.findtext("title") or "").strip()
                        link = (item.findtext("link") or "").strip()
                        headline = title.rsplit(" - ", 1)[0]
                        if not link.startswith("https://") or not PELLET.search(headline):
                            continue
                        for match in ORG.finditer(headline):
                            name = re.sub(r"\s+", " ", match.group(1)).strip(" ,.-")
                            if len(name) < 7 or BLOCK.match(name):
                                continue
                            key = (name.casefold(), country, sector)
                            rec = existing.setdefault(key, {
                                "company_name": name,
                                "country_context": country,
                                "sector": sector,
                                "company_size": "unknown",
                                "classification": "unverified_news_mention",
                                "wood_pellet_use_confirmed": False,
                                "official_website": None,
                                "public_business_email": None,
                                "source_urls": [],
                                "first_seen": now
                            })
                            links = rec.setdefault("source_urls", [])
                            if link not in links and len(links) < 5:
                                links.append(link)
                except (OSError, ValueError, ET.ParseError) as exc:
                    errors.append({"country": country, "sector": sector,
                                   "error": type(exc).__name__})
                time.sleep(0.05)
    rows = sorted(existing.values(), key=lambda r: (
        str(r.get("country_context", "")), str(r.get("company_name", "")),
        str(r.get("sector", ""))))[:1500]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated_at": now,
        "source": "Google News public RSS",
        "method": "public_news_candidate_extraction_v5.3",
        "disclaimer": "UNVERIFIED news mentions only. Country is search context, "
                      "not confirmed HQ. No company size, actual pellet use, "
                      "purchase intent, website, or email verified.",
        "stats": {"queries_attempted": queries_run,
                  "articles_checked": articles_checked,
                  "candidate_records": len(rows),
                  "feed_errors": len(errors)},
        "items": rows, "errors": errors[:50]
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Queries={queries_run}; articles={articles_checked}; "
          f"candidates={len(rows)}; errors={len(errors)}")

if __name__ == "__main__":
    main()
