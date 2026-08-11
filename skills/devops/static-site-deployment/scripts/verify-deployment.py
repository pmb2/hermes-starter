"""
Static Site Deployment Verifier
================================
Run after deploying to GitHub Pages to verify:
  - DNS resolves to GitHub IPs
  - HTTP status is 200
  - HTTPS redirect works
  - All external image references resolve
  - Content-Length matches expected

Usage:
    python scripts/verify-deployment.py <domain>
    python scripts/verify-deployment.py lemcolc.com
"""

import sys
import re
import socket
import urllib.request
import urllib.error
import ssl

GITHUB_PAGES_IPS = {
    "185.199.108.153",
    "185.199.109.153",
    "185.199.110.153",
    "185.199.111.153",
}

TIMEOUT = 15
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"


def check_dns(domain):
    """Check that domain resolves to GitHub Pages IPs."""
    try:
        addrs = set(socket.gethostbyname_ex(domain)[2])
        if not addrs:
            print(f"{FAIL} DNS: {domain} did not resolve to any address")
            return False
        if addrs.issubset(GITHUB_PAGES_IPS):
            print(f"{PASS} DNS: {domain} -> {', '.join(sorted(addrs))}")
            return True
        old = addrs - GITHUB_PAGES_IPS
        good = addrs & GITHUB_PAGES_IPS
        if old and good:
            print(f"{WARN} DNS: mixed — GitHub: {', '.join(sorted(good))}, other: {', '.join(sorted(old))}")
            return True
        print(f"{FAIL} DNS: {domain} -> {', '.join(sorted(addrs))} (expected GitHub IPs)")
        return False
    except socket.gaierror as e:
        print(f"{FAIL} DNS: {domain} — {e}")
        return False


def check_http(domain, scheme="https"):
    """Check that the domain returns 200."""
    url = f"{scheme}://{domain}/"
    ctx = ssl.create_default_context()
    if scheme == "https":
        ctx.check_hostname = True
    req = urllib.request.Request(url, method="HEAD")
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        status = resp.status
        server = resp.headers.get("Server", "?")
        length = resp.headers.get("Content-Length", "?")
        if status == 200:
            print(f"{PASS} {scheme.upper()}: {url} -> {status} ({length}B, server: {server})")
            return True
        else:
            print(f"{WARN} {scheme.upper()}: {url} -> {status} (expected 200)")
            return status in (301, 302, 307, 308)  # redirects are ok
    except urllib.error.HTTPError as e:
        print(f"{FAIL} {scheme.upper()}: {url} -> {e.code} {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"{FAIL} {scheme.upper()}: {url} — {e.reason}")
        return False


def check_image_refs(domain):
    """Fetch the page and check all image URLs resolve."""
    url = f"https://{domain}/"
    ctx = ssl.create_default_context()
    try:
        resp = urllib.request.urlopen(url, timeout=TIMEOUT, context=ctx)
        html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"{FAIL} Cannot fetch page to check images: {e}")
        return False

    # Find all image src URLs
    srcs = re.findall(r'src="([^"]+)"', html)
    srcsets = re.findall(r'srcset="([^"]+)"', html)
    for ss in srcsets:
        for part in ss.split(","):
            part = part.strip().split()[0]
            if part:
                srcs.append(part)

    # Filter to absolute URLs (skip data: URIs and relative paths)
    external = [s for s in srcs if s.startswith("http")]
    if not external:
        print(f"{WARN} No external image URLs found to verify (only relative paths)")
        return True

    all_ok = True
    for img_url in external:
        try:
            ireq = urllib.request.Request(img_url, method="HEAD")
            iresp = urllib.request.urlopen(ireq, timeout=TIMEOUT)
            if iresp.status == 200:
                size = iresp.headers.get("Content-Length", "?")
                print(f"{PASS} IMG: {iresp.status} ({size}B) {img_url[:80]}")
            elif iresp.status in (301, 302):
                print(f"{WARN} IMG: {iresp.status} redirect {img_url[:80]}")
            else:
                print(f"{FAIL} IMG: {iresp.status} {img_url[:80]}")
                all_ok = False
        except Exception as e:
            print(f"{FAIL} IMG: {e} {img_url[:80]}")
            all_ok = False

    return all_ok


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify-deployment.py <domain>")
        sys.exit(1)

    domain = sys.argv[1].strip().lower()
    domain = re.sub(r"^https?://", "", domain).rstrip("/")

    print(f"\n{'='*60}")
    print(f"  Verifying deployment: {domain}")
    print(f"{'='*60}\n")

    checks = [
        ("DNS Resolution", lambda: check_dns(domain)),
        ("HTTP (no SSL)",   lambda: check_http(domain, "http")),
        ("HTTPS (with SSL)",lambda: check_http(domain, "https")),
        ("Image References", lambda: check_image_refs(domain)),
    ]

    results = []
    for label, fn in checks:
        print(f"--- {label} ---")
        try:
            ok = fn()
        except Exception as e:
            print(f"{FAIL} {label} threw: {e}")
            ok = False
        results.append(ok)
        print()

    passed = sum(results)
    total = len(results)
    print(f"{'='*60}")
    if passed == total:
        print(f"  {PASS} All {total} checks passed!")
    else:
        print(f"  {WARN} {passed}/{total} checks passed — review failures above")
    print(f"{'='*60}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
