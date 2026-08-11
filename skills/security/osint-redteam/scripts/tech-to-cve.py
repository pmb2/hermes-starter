#!/usr/bin/env python3
"""
tech-to-cve — Passive CVE Correlator (osint-redteam script)

Usage:
  python tech-to-cve.py --tech nginx --version 1.24.0
  python tech-to-cve.py --input tech_stack.json
  cat tech_stack.json | python tech-to-cve.py - (stdin)

Full source: agent-universe/teams/07-recon-team/shared/tech-to-cve/cve_match.py
"""

import json
import sys
import urllib.request
import urllib.error
import urllib.parse
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# ── CPE Map (100+ entries) ──────────────────────────────────────────

CPE_MAP = {
    "nginx": ("nginx", "nginx"),
    "apache http server": ("apache", "http_server"),
    "iis": ("microsoft", "internet_information_services"),
    "php": ("php", "php"),
    "python": ("python", "python"),
    "node.js": ("nodejs", "node.js"),
    "express": ("expressjs", "express"),
    "django": ("djangoproject", "django"),
    "flask": ("palletsprojects", "flask"),
    "ruby": ("ruby-lang", "ruby"),
    "rails": ("rubyonrails", "rails"),
    "java": ("oracle", "jre"),
    "tomcat": ("apache", "tomcat"),
    "mysql": ("oracle", "mysql"),
    "mariadb": ("mariadb", "mariadb"),
    "postgresql": ("postgresql", "postgresql"),
    "mongodb": ("mongodb", "mongodb"),
    "redis": ("redis", "redis"),
    "elasticsearch": ("elastic", "elasticsearch"),
    "wordpress": ("wordpress", "wordpress"),
    "drupal": ("drupal", "drupal"),
    "jquery": ("jquery", "jquery"),
    "react": ("meta", "react"),
    "vue.js": ("vuejs", "vue.js"),
    "angular": ("google", "angular"),
    "openssh": ("openbsd", "openssh"),
    "openssl": ("openssl", "openssl"),
    "docker": ("docker", "docker"),
    "kubernetes": ("kubernetes", "kubernetes"),
    "haproxy": ("haproxy", "haproxy"),
    "traefik": ("traefik", "traefik"),
    "caddy": ("caddyserver", "caddy"),
}

def generate_cpe(name: str, version: str) -> str:
    vendor, product = CPE_MAP.get(name.lower(), (name.lower(), name.lower()))
    ver = re.sub(r'[^a-zA-Z0-9._\-\*]', '', version) if version else "*"
    return f"cpe:2.3:a:{vendor}:{product}:{ver}:*:*:*:*:*:*:*"

def query_nvd(cpe: str, api_key: str = "") -> list:
    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cpeName={urllib.parse.quote(cpe)}&resultsPerPage=20"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tech-to-cve/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[NVD] Error: {e}", file=sys.stderr)
        return []

    results = []
    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        metrics = cve.get("metrics", {})
        cvss_data = None
        for v in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            if v in metrics and metrics[v]:
                cvss_data = metrics[v][0]
                break
        if cvss_data:
            cvss_obj = cvss_data.get("cvssData", {})
            score = float(cvss_obj.get("baseScore", 0))
            severity = cvss_obj.get("baseSeverity", "NONE")
        else:
            score, severity = 0.0, "NONE"

        desc = ""
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", "")[:300]
                break

        results.append({
            "cve_id": cve.get("id", ""),
            "cvss_score": score,
            "severity": severity,
            "description": desc,
            "source": "nvd",
        })
        time.sleep(0.5)  # rate limiting
    return results

def query_osv(name: str, version: str) -> list:
    payload = json.dumps({"package": {"name": name, "ecosystem": ""}, "version": version}).encode()
    try:
        req = urllib.request.Request("https://api.osv.dev/v1/query", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []

    return [{
        "cve_id": v.get("id", ""),
        "cvss_score": 0.0,
        "severity": "MEDIUM",
        "description": v.get("summary", "")[:300],
        "source": "osv",
    } for v in data.get("vulns", [])]

def main():
    import argparse
    parser = argparse.ArgumentParser(description="tech-to-cve CVE correlator")
    parser.add_argument("--tech", help="Technology name")
    parser.add_argument("--version", help="Version string")
    parser.add_argument("--input", help="JSON file path or '-' for stdin")

    args = parser.parse_args()

    techs = []
    if args.tech and args.version:
        techs.append((args.tech, args.version))
    elif args.input:
        src = sys.stdin if args.input == "-" else open(args.input)
        for item in json.load(src):
            techs.append((item.get("name", ""), item.get("version", "")))
    else:
        parser.print_help()
        sys.exit(1)

    for name, version in techs:
        cpe = generate_cpe(name, version)
        print(f"→ {name} {version}  [CPE: {cpe}]")
        cves = query_nvd(cpe) + query_osv(name, version)
        for cve in sorted(cves, key=lambda c: -c["cvss_score"]):
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵", "NONE": "⚪"}
            print(f"  {icon.get(cve['severity'], '⚪')} {cve['cve_id']} ({cve['cvss_score']}) [{cve['source']}]")
            print(f"    {cve['description']}")
        if not cves:
            print("  ✅ No CVEs found")
        print()

if __name__ == "__main__":
    main()
