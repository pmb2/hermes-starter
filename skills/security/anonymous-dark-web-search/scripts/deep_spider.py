#!/usr/bin/env python3
"""
Deep Spider — Anonymous Telegram + Dark Web Search Engine
Routes all traffic through Tor SOCKS5 (127.0.0.1:9050)

Usage:
  python deep_spider.py telegram --keywords "breach data,stealer logs,marketplace"
  python deep_spider.py darkweb --keywords "credentials,dumps,ransomware"
  python deep_spider.py sweep --keywords "breach,leak,dump" --all
  python deep_spider.py new-identity    # Request fresh Tor circuit
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime

import requests

# socks5h = resolve hostnames THROUGH Tor (required for .onion addresses)
# The 'h' suffix is critical — without it, DNS resolves locally and .onion fails
TOR_PROXY = "socks5h://127.0.0.1:9050"
TOR_CONTROL_HOST = "127.0.0.1"
TOR_CONTROL_PORT = 9051

RESULTS_DIR = os.path.expanduser("~/deep-spider/results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.proxies = {"http": TOR_PROXY, "https": TOR_PROXY}
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:128.0) Gecko/20100101 Firefox/128.0"
})
SESSION.timeout = 30


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def save_results(source, keyword, results):
    safe_kw = re.sub(r'[^a-z0-9]+', '_', keyword.lower())[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"{source}_{safe_kw}_{ts}.json")
    with open(path, "w") as f:
        json.dump({"source": source, "keyword": keyword, "timestamp": ts,
                    "count": len(results), "results": results}, f, indent=2)
    log(f"Saved {len(results)} results → {path}")
    return path


def new_tor_identity():
    """Request fresh Tor circuit (NEWNYM)"""
    try:
        from stem import Signal
        from stem.control import Controller
        with Controller.from_port(port=TOR_CONTROL_PORT) as ctrl:
            ctrl.authenticate()
            ctrl.signal(Signal.NEWNYM)
        log("New Tor identity requested — circuit rotated")
        return True
    except Exception as e:
        log(f"Identity rotation failed: {e}")
        return False


def fetch(url, retries=3):
    for i in range(retries):
        try:
            resp = SESSION.get(url)
            if resp.status_code == 200:
                return resp
            log(f"HTTP {resp.status_code} on {url[:80]}")
        except Exception as e:
            if i < retries - 1:
                wait = 2 ** i + random.random()
                log(f"Retry {i+1}/{retries} in {wait:.1f}s: {e}")
                time.sleep(wait)
            else:
                log(f"Failed after {retries} retries: {e}")
    return None


# ─── Telegram Search ───────────────────────────────────────────────

def search_telegram(keywords, max_results=50):
    """
    Search Telegram via public web interfaces through Tor.
    Sources:
    1. t.me search (Telegram web search)
    2. TGStat (Telegram channel analytics)
    3. Telemetr (Telegram channel stats)
    """
    results = []
    seen_urls = set()
    kw_list = [k.strip() for k in keywords.split(",")]

    for kw in kw_list[:5]:
        log(f"Searching Telegram for: {kw}")

        # Method 1: t.me/search (Telegram's own web search)
        for attempt_url in [
            f"https://t.me/search?q={urllib.parse.quote(kw)}",
            f"https://t.me/s/{urllib.parse.quote(kw)}",
        ]:
            resp = fetch(attempt_url)
            if resp:
                links = re.findall(r'href="(https://t\.me/[a-zA-Z0-9_]+(?:/[\d]+)?)"', resp.text)
                for link in links:
                    if link not in seen_urls:
                        seen_urls.add(link)
                        results.append({
                            "type": "telegram",
                            "source": "t.me",
                            "keyword": kw,
                            "url": link,
                            "title": "",
                            "snippet": ""
                        })
                if links:
                    log(f"  Found {len(links)} links on t.me")
                break  # One worked, move on

        # Method 2: TGStat search
        tgstat_url = f"https://tgstat.com/search?q={urllib.parse.quote(kw)}"
        resp = fetch(tgstat_url)
        if resp:
            channel_links = re.findall(r'href="/en/([a-zA-Z0-9_@]+)"', resp.text)
            for ch in channel_links[:10]:
                url = f"https://t.me/{ch}"
                if url not in seen_urls:
                    seen_urls.add(url)
                    results.append({
                        "type": "telegram_channel",
                        "source": "tgstat",
                        "keyword": kw,
                        "url": url,
                        "title": ch,
                        "snippet": ""
                    })
            if channel_links:
                log(f"  Found {len(channel_links)} channels on tgstat")

        # Method 3: Telemetr.io
        telemetr_url = f"https://telemetr.io/search?q={urllib.parse.quote(kw)}"
        resp = fetch(telemetr_url)
        if resp:
            links = re.findall(r'href="(https://t\.me/[a-zA-Z0-9_]+)"', resp.text)
            for link in links:
                if link not in seen_urls:
                    seen_urls.add(link)
                    results.append({
                        "type": "telegram_channel",
                        "source": "telemetr",
                        "keyword": kw,
                        "url": link,
                        "title": "",
                        "snippet": ""
                    })
            if links:
                log(f"  Found {len(links)} channels on telemetr")

        time.sleep(random.uniform(3, 5))

    return results[:max_results]


# ─── Dark Web Search ──────────────────────────────────────────────

DARKWEB_SEARCH_ENGINES = [
    # Ahmia — clearnet .onion indexer (most reliable through Tor)
    {
        "name": "ahmia",
        "url": "https://ahmia.fi/search/?q={query}",
        "parser": "ahmia",
    },
    # OnionLand — clearnet .onion search engine
    {
        "name": "onionland",
        "url": "https://onionland.io/search?q={query}",
        "parser": "generic",
    },
    # DarkEye — clearnet .onion crawler
    {
        "name": "darkeye",
        "url": "https://darkeye.biz/search?q={query}",
        "parser": "generic",
    },
    # Torch — oldest .onion search engine (via Tor)
    {
        "name": "torch",
        "url": "http://torchdeedp3i2jigzjxm4kq4x4oonm5sh3x2lowp4p4y5q5n6l2iyd.onion/search?q={query}",
        "parser": "ahmia",
    },
    # Excavator — clearnet dark web search
    {
        "name": "excavator",
        "url": "https://excavator.zone/search?q={query}",
        "parser": "generic",
    },
]


def parse_ahmia(html):
    """Parse Ahmia search results"""
    results = []
    blocks = re.findall(r'<li[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL)
    if not blocks:
        # Fallback: find onion links anywhere
        onions = re.findall(r'([a-z2-7]{16,56}\.onion)', html)
        for o in onions[:20]:
            results.append({"url": f"http://{o}", "title": o, "snippet": ""})
        return results

    for block in blocks:
        title_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', block)
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
        if title_match:
            url = title_match.group(1)
            if not url.startswith("http"):
                url = "http://" + url
            results.append({
                "url": url,
                "title": title_match.group(2).strip(),
                "snippet": snippet_match.group(1).strip() if snippet_match else "",
            })

    # Also scan for any .onion links in the whole page
    onions = re.findall(r'([a-z2-7]{16,56}\.onion)', html)
    existing_urls = {r["url"] for r in results}
    for o in onions:
        url = f"http://{o}"
        if url not in existing_urls:
            results.append({"url": url, "title": o, "snippet": ""})
            existing_urls.add(url)

    return results


def parse_generic(html):
    """Generic result parser — find all .onion links"""
    results = []
    onions = re.findall(r'([a-z2-7]{16,56}\.onion)', html)
    seen = set()
    for o in onions:
        url = f"http://{o}"
        if url not in seen:
            results.append({"url": url, "title": o, "snippet": ""})
            seen.add(url)

    links = re.findall(r'href="(https?://[^"]+)"', html)
    for url in links[:20]:
        if ".onion" in url and url not in seen:
            results.append({"url": url, "title": url, "snippet": ""})
            seen.add(url)

    return results


PARSERS = {
    "ahmia": parse_ahmia,
    "generic": parse_generic,
}


def search_darkweb(keywords, max_results=100):
    results = []
    kw_list = [k.strip() for k in keywords.split(",")]

    for kw in kw_list[:3]:
        log(f"Searching dark web for: {kw}")

        for engine in DARKWEB_SEARCH_ENGINES:
            url = engine["url"].format(query=urllib.parse.quote(kw))
            log(f"  Querying {engine['name']}...")
            resp = fetch(url)
            if resp and len(resp.text) > 200:
                parser = PARSERS.get(engine["parser"], parse_generic)
                engine_results = parser(resp.text)
                for r in engine_results:
                    r["source_engine"] = engine["name"]
                    r["keyword"] = kw
                results.extend(engine_results)
                log(f"    → {len(engine_results)} results")
            else:
                log(f"    → no response from {engine['name']}")

            time.sleep(random.uniform(3, 6))

        # Rotate identity between keyword sets
        if kw != kw_list[-1]:
            new_tor_identity()
            time.sleep(5)

    return results[:max_results]


# ─── Surface Web Intel (clearnet sources) ─────────────────────────

SURFACE_INTEL_SOURCES = [
    {"name": "pastebin_archive", "url": "https://psbdmp.ws/search?q={query}"},
    {"name": "breach_forum_search", "url": "https://breachforums.st/search.php?q={query}"},
    {"name": "intelx_public", "url": "https://intelx.io/?s={query}"},
]


def search_surface_intel(keywords, max_results=50):
    results = []
    kw_list = [k.strip() for k in keywords.split(",")]
    for kw in kw_list[:3]:
        for source in SURFACE_INTEL_SOURCES:
            url = source["url"].format(query=urllib.parse.quote(kw))
            log(f"Checking {source['name']} for: {kw}")
            resp = fetch(url)
            if resp:
                links = re.findall(r'href="(https?://[^"]+)"', resp.text)
                for link in links[:10]:
                    results.append({
                        "type": "surface_intel",
                        "source": source["name"],
                        "keyword": kw,
                        "url": link,
                    })
            time.sleep(random.uniform(1, 3))
    return results[:max_results]


# ─── CLI ──────────────────────────────────────────────────────────

def cmd_telegram(args):
    log("=== Telegram Search (via Tor) ===")
    results = search_telegram(args.keywords, args.limit)
    path = save_results("telegram", args.keywords, results)
    print(f"\n{'='*60}\nTELEGRAM RESULTS: {len(results)} hits\n{'='*60}")
    for r in results[:20]:
        url = r.get("url", "")
        title = r.get("title", "")
        src = r.get("source", "")
        print(f"  [{src}] {title[:80] if title else url[:80]}\n         {url}")
    if len(results) > 20:
        print(f"  ... and {len(results)-20} more (see {path})")


def cmd_darkweb(args):
    log("=== Dark Web Search (via Tor) ===")
    results = search_darkweb(args.keywords, args.limit)
    path = save_results("darkweb", args.keywords, results)
    print(f"\n{'='*60}\nDARK WEB RESULTS: {len(results)} hits\n{'='*60}")
    shown = 0
    for r in results:
        if shown >= 20:
            break
        url = r.get("url", "")
        title = r.get("title", "")
        eng = r.get("source_engine", "?")
        print(f"  [{eng}] {title[:80] if title != url else ''}\n         {url}")
        shown += 1
    if len(results) > 20:
        print(f"  ... and {len(results)-20} more (see {path})")


def cmd_sweep(args):
    log("=== Full Sweep (Telegram + Dark Web + Surface Intel) ===")
    tg_results = search_telegram(args.keywords, args.limit // 2)
    save_results("sweep_telegram", args.keywords, tg_results)
    new_tor_identity()
    time.sleep(5)
    dw_results = search_darkweb(args.keywords, args.limit)
    save_results("sweep_darkweb", args.keywords, dw_results)
    si_results = search_surface_intel(args.keywords, args.limit // 2)
    save_results("sweep_surface", args.keywords, si_results)
    total = len(tg_results) + len(dw_results) + len(si_results)
    print(f"\n{'='*60}\nSWEEP COMPLETE: {total} total results\n"
          f"  Telegram: {len(tg_results)}\n  Dark Web: {len(dw_results)}\n"
          f"  Surface:  {len(si_results)}\n  Saved to: {RESULTS_DIR}")


def cmd_newid(args):
    new_tor_identity()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deep Spider — Anonymous Telegram + Dark Web Search")
    subparsers = parser.add_subparsers(dest="command")

    p_tg = subparsers.add_parser("telegram", help="Search Telegram through Tor")
    p_tg.add_argument("--keywords", "-k", required=True)
    p_tg.add_argument("--limit", "-l", type=int, default=50)

    p_dw = subparsers.add_parser("darkweb", help="Search dark web through Tor")
    p_dw.add_argument("--keywords", "-k", required=True)
    p_dw.add_argument("--limit", "-l", type=int, default=100)

    p_sw = subparsers.add_parser("sweep", help="Full sweep: Telegram + Dark Web + Surface Intel")
    p_sw.add_argument("--keywords", "-k", required=True)
    p_sw.add_argument("--limit", "-l", type=int, default=100)

    subparsers.add_parser("new-identity", help="Request fresh Tor circuit")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        resp = requests.get("https://check.torproject.org/api/ip",
                           proxies={"http": TOR_PROXY, "https": TOR_PROXY}, timeout=10)
        if resp.json().get("IsTor") is True:
            log(f"Tor verified — exit node: {resp.json().get('IP', 'unknown')}")
        else:
            log("WARNING: Not routing through Tor!")
    except Exception as e:
        log(f"WARNING: Tor check failed ({e}) — is Tor running on 127.0.0.1:9050?")

    if args.command == "telegram":
        cmd_telegram(args)
    elif args.command == "darkweb":
        cmd_darkweb(args)
    elif args.command == "sweep":
        cmd_sweep(args)
    elif args.command == "new-identity":
        cmd_newid(args)
