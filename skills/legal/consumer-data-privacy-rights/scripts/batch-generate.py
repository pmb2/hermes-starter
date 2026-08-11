#!/usr/bin/env python3
"""
Batch DSAR + Deletion Letter Generator
========================================
Reads personal_config.yaml and the merged broker CSV,
then generates filled-in CCPA/CPRA combined request letters
for all specified services.

Usage:
  python3 batch_generate.py --priority credit     # Credit bureaus
  python3 batch_generate.py --priority people     # People search sites
  python3 batch_generate.py --priority marketing  # Marketing/B2B
  python3 batch_generate.py --priority all        # ALL 1,837 brokers
  python3 batch_generate.py --service "Acxiom"    # Single service

Output:
  ./services/[service-name]/001-combined-request.txt
"""

import csv, os, sys, datetime, re, yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = BASE_DIR / "personal_config.yaml"
BROKERS_CSV = BASE_DIR / "merged_brokers.csv"
SERVICES_DIR = BASE_DIR / "services"
TS = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
DS = datetime.datetime.now().strftime("%Y-%m-%d")

with open(CONFIG_PATH) as f:
    PI = yaml.safe_load(f)["personal_info"]


def etag(name):
    return f"{PI['email_base'].replace('@gmail.com','')}+{re.sub(r'[^a-zA-Z0-9]','',name.lower())[:15]}@gmail.com"


def gen(broker):
    name = broker["Name"].strip()
    web = broker.get("Website","").strip()
    ou = broker.get("OptOut URL","").strip()
    ce = broker.get("Privacy Email","").strip()
    bt = broker.get("Type","").strip()
    if not ce and web:
        ce = "privacy@" + re.sub(r'https?://(?:www\.)?([^/]+).*',r'\1',web)
    te = etag(name)
    sn = re.sub(r'[^a-z0-9_-]','_',name.lower())[:50]
    sd = SERVICES_DIR / sn
    sd.mkdir(parents=True, exist_ok=True)

    l = f"""============================================================
COMBINED CCPA/CPRA DATA RIGHTS REQUEST
============================================================
Generated: {TS} | Target: {name}
Contact: {ce} | From: {PI['full_name']} <{te}>
============================================================

{DS}

VIA EMAIL: {ce}
{'VIA WEB FORM: ' + ou if ou else ''}

{name}
Attn: Privacy Officer / Legal Department

RE: COMBINED DATA SUBJECT ACCESS AND DELETION REQUEST (CCPA/CPRA)

PART I — RIGHT TO KNOW (§ 1798.110): I request complete disclosure of
all personal information collected about me: categories, sources, business
purpose, third parties shared with, and a FULL DATA EXPORT in portable format.

PART II — RIGHT TO DELETE (§ 1798.105): Upon receipt of the above, delete
ALL personal information and notify all service providers and third parties.

IDENTIFICATION:
  Name: {PI['full_name']} | Email: {te} | Phone: {PI.get('phone','[TBD]')}
  Address: {PI['address']}, {PI['city_state_zip']} | DOB: {PI['dob']}

Acknowledge within 10 days. Respond within 45 days.
Non-compliance: $2,500/violation under § 1798.155.

Sincerely,
{PI['full_name']}
{te}
---
{safe_name}-{DS} | github.com/pmb2/data-privacy-pipeline
"""
    (sd / "001-combined-request.txt").write_text(l, encoding="utf-8")
    return sn


def main():
    kw = {"credit": ["equifax","experian","transunion","lexisnexis","innovis",
                     "chexsystems","early warning","clarity services","sagestream",
                     "checkr","hireright","first advantage"],
          "people": ["spokeo","whitepages","411.com","beenverified","truthfinder",
                     "intelius","radaris","mylife","peoplefinders","fastpeoplesearch",
                     "truepeoplesearch","nuwber","peekyou","checkpeople","peoplelooker",
                     "us search","thatsthem","familytreenow","zabasearch"],
          "marketing": ["acxiom","epsilon","oracle data","liveramp","the trade desk",
                        "criteo","tapad","lotame","zeta global","zoominfo","apollo.io",
                        "seamless","lusha","clearbit","rocketreach","crunchbase",
                        "6sense","demandbase","bombora"]}

    if len(sys.argv) < 2 or sys.argv[1] in ("-h","--help","help"):
        print(__doc__); return
    if sys.argv[1] == "--priority":
        with open(BROKERS_CSV) as f:
            brokers = list(csv.DictReader(f))
        if sys.argv[2] == "all":
            targets = brokers
        else:
            targets = [b for b in brokers if any(k in b["Name"].lower() for k in kw.get(sys.argv[2],[]))]
        for b in targets:
            gen(b); print(f"  {b['Name']}")
        print(f"\n{len(targets)} letters generated ({sys.argv[2]})")
    elif sys.argv[1] == "--service":
        with open(BROKERS_CSV) as f:
            for b in csv.DictReader(f):
                if sys.argv[2].lower() in b["Name"].lower():
                    gen(b); print(f"  {b['Name']}"); return
        print(f"Not found: {sys.argv[2]}")

if __name__ == "__main__":
    main()
