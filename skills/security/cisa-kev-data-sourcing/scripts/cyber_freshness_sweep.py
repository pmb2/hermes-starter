#!/usr/bin/env python3
"""cyber_freshness_sweep.py — standalone morning-briefing freshness sweep.

Fetches three reliable, guard-friendly sources in one run:
  1. CISA KEV JSON feed (gzip-aware) — filter by dateAdded, surface due dates
  2. PoC-in-GitHub README (top 40 CVE lines; newest additions at top)
  3. Google News RSS (cybersecurity headlines with pubDate)

Usage:  python cyber_freshness_sweep.py [YYYY-MM-DD]
  Optional arg: earliest dateAdded to surface from KEV (default: first of
  current month).

Run as a script FILE, not an inline `curl && python -c` chain — inline chains
can trip Hermes terminal command guards and break on Windows/MSYS quoting.
KEV entries whose dueDate is TODAY or TOMORROW are Tier 1 briefing material.
"""
import gzip
import io
import json
import re
import sys
import urllib.request
from datetime import date

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or url.endswith(".gz"):
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        return data


def cisa_kev(since):
    raw = fetch("https://cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json")
    d = json.loads(raw.decode("utf-8", errors="replace"))
    vulns = d.get("vulnerabilities", [])
    print(f"catalogVersion: {d.get('catalogVersion')} | total: {len(vulns)}")
    recent = [v for v in vulns if v.get("dateAdded", "") >= since]
    print(f"dateAdded >= {since}: {len(recent)}")
    for v in sorted(recent, key=lambda x: x["dateAdded"], reverse=True)[:20]:
        print(v["dateAdded"], "|", v["cveID"], "|", v.get("vendorProject"),
              "|", v.get("product"), "| due:", v.get("dueDate"))


def poc_github():
    raw = fetch("https://raw.githubusercontent.com/nomi-sec/PoC-in-GitHub/master/README.md", timeout=30)
    lines = raw.decode("utf-8", errors="replace").splitlines()
    cves = [l for l in lines if re.search(r"CVE-\d{4}-\d{4,7}", l)]
    for l in cves[:40]:
        print(l.strip()[:160])


def news_rss():
    raw = fetch("https://news.google.com/rss/search?q=cybersecurity+OR+zero-day+OR+ransomware+OR+breach&hl=en-US&gl=US&ceid=US:en")
    text = raw.decode("utf-8", errors="replace")
    items = re.findall(r"<item>.*?<title>(.*?)</title>.*?<pubDate>(.*?)</pubDate>", text, re.S)
    for t, p in items[:15]:
        print(p.strip(), "|", re.sub(r"<[^>]+>", "", t).strip()[:120])


if __name__ == "__main__":
    since = sys.argv[1] if len(sys.argv) > 1 else date.today().replace(day=1).isoformat()
    print("=== CISA KEV ===")
    cisa_kev(since)
    print("\n=== PoC-in-GitHub (top 40) ===")
    poc_github()
    print("\n=== Google News RSS ===")
    news_rss()
