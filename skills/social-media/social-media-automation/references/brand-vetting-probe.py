#!/usr/bin/env python3
"""
brand-vetting-probe.py
Reusable probe for vetting a new brand name across domains, social handles,
GitHub, and exact-phrase search. Run before committing to a brand name.

Usage:
    python brand-vetting-probe.py <handle> <"Brand Name">

Example:
    python brand-vetting-probe.py gradientrun "Gradient Run"
"""
import socket
import ssl
import sys
import urllib.request
import re

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def dns_available(domain: str) -> bool:
    try:
        socket.gethostbyname(domain)
        return False
    except socket.gaierror:
        return True
    except Exception:
        return False


def fetch_title(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=CTX) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip().replace("\n", " ")[:120]
    except Exception as e:
        return f"ERR: {type(e).__name__}"
    return ""


def looks_like_profile(platform: str, title: str, handle: str) -> bool:
    t = title.lower()
    h = handle.lower().replace("_", "")
    if platform == "x":
        return "@" in title and h in t
    if platform == "instagram":
        return "instagram photos" in t or h in t.replace(" ", "")
    if platform == "youtube":
        return "youtube" in t and h in t.replace(" ", "")
    return h in t.replace(" ", "")


def check_social(platform: str, url: str, handle: str) -> tuple:
    title = fetch_title(url)
    if title.startswith("ERR:"):
        return title, False
    taken = looks_like_profile(platform, title, handle)
    return title, taken


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    handle = sys.argv[1]
    brand = sys.argv[2] if len(sys.argv) > 2 else handle

    print(f"Vetting brand: {brand} (handle: {handle})\n")

    # Domains
    suffixes = ["com", "co", "io", "ai", "app"]
    domain_avail = {}
    for suf in suffixes:
        d = f"{handle}.{suf}"
        avail = dns_available(d)
        domain_avail[d] = avail
        status = "AVAIL" if avail else "TAKEN"
        print(f"Domain {d}: {status}")

    # Social / platform handles
    checks = [
        ("X", f"https://x.com/{handle}"),
        ("Instagram", f"https://www.instagram.com/{handle}/"),
        ("YouTube", f"https://www.youtube.com/@{handle}"),
        ("GitHub", f"https://github.com/{handle}"),
        ("LinkedIn", f"https://www.linkedin.com/company/{handle}/"),
        ("Reddit", f"https://www.reddit.com/r/{handle}/"),
        ("Bluesky", f"https://bsky.app/profile/{handle}.bsky.social"),
        ("Threads", f"https://www.threads.net/@{handle}"),
        ("Pinterest", f"https://www.pinterest.com/{handle}/"),
        ("Substack", f"https://{handle}.substack.com/"),
        ("Medium", f"https://medium.com/@{handle}"),
        ("beehiiv", f"https://{handle}.beehiiv.com/"),
    ]

    social_taken = 0
    for platform, url in checks:
        title, taken = check_social(platform.lower(), url, handle)
        social_taken += int(taken)
        status = "TAKEN" if taken else "AVAIL/ERR"
        print(f"{platform}: {status} ({title[:80]})")

    # Google exact phrase result count (best effort)
    query = brand.replace(" ", "+")
    try:
        req = urllib.request.Request(
            f"https://www.google.com/search?q=%22{query}%22&num=10",
            headers=HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10, context=CTX) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.I | re.S)
        print(f"\nGoogle exact-phrase results: {len(titles)}")
        for t in titles[:3]:
            print(f"  - {re.sub(r'<[^>]+>', '', t)[:100]}")
    except Exception as e:
        print(f"\nGoogle search failed: {type(e).__name__}")

    # Summary
    domain_avail_count = sum(domain_avail.values())
    print(f"\nSummary: {domain_avail_count}/{len(suffixes)} core domains available, {social_taken}/{len(checks)} social handles taken")
    if domain_avail_count >= 3 and social_taken <= 1:
        print("-> STRONG candidate")
    elif domain_avail_count >= 2 and social_taken <= 3:
        print("-> VIABLE candidate with compromises")
    else:
        print("-> WEAK candidate; pick a different name")


if __name__ == "__main__":
    main()
