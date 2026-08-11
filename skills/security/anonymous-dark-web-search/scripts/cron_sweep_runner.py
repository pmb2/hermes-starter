#!/usr/bin/env python3
"""
Cron-ready sweep runner.
Starts Tor if not running, executes dark web sweep, prints summary.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

DEEP_SPIDER = os.path.expanduser("~/deep-spider")
TORRC = os.path.join(DEEP_SPIDER, "torrc")
TOR_BIN = r"C:\ProgramData\chocolatey\bin\tor.exe"


def check_tor():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect(("127.0.0.1", 9050))
        s.close()
        return True
    except:
        return False


def start_tor():
    log = open(os.path.join(DEEP_SPIDER, "tor_bg.log"), "a")
    proc = subprocess.Popen(
        [TOR_BIN, "-f", TORRC],
        stdout=log, stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    for i in range(15):
        time.sleep(1)
        if check_tor():
            return proc.pid
    return None


def run_spider(cmd_args):
    result = subprocess.run(
        [sys.executable, os.path.join(DEEP_SPIDER, "deep_spider.py")] + cmd_args,
        capture_output=True, text=True, timeout=180, cwd=DEEP_SPIDER
    )
    return result.stdout + result.stderr


def new_tor_identity():
    try:
        from stem import Signal
        from stem.control import Controller
        with Controller.from_port(port=9051) as ctrl:
            ctrl.authenticate()
            ctrl.signal(Signal.NEWNYM)
        return True
    except:
        return False


def main():
    print(f"🔥 DEEP SPIDER SWEEP | {datetime.now().strftime('%b %d, %Y %H:%M ET')}\n")

    if not check_tor():
        print("[*] Tor not running — starting...")
        pid = start_tor()
        if pid:
            print(f"[+] Tor started (PID {pid})")
        else:
            print("[!] FAILED to start Tor!")
            sys.exit(1)
    else:
        print("[✓] Tor SOCKS5 reachable on 127.0.0.1:9050")

    try:
        import requests
        resp = requests.get("https://check.torproject.org/api/ip",
                           proxies={"http": "socks5h://127.0.0.1:9050",
                                    "https": "socks5h://127.0.0.1:9050"},
                           timeout=15)
        data = resp.json()
        print(f"[✓] Tor exit node: {data.get('IP', 'unknown')}\n")
    except Exception as e:
        print(f"[!] Tor verification failed: {e}")
        sys.exit(1)

    print("━━━ PHASE 1: BREACH & CREDENTIAL SEARCH ━━━")
    output1 = run_spider([
        "darkweb", "--keywords",
        "breached data leaked database,credentials dump stealer logs,ransomware leak marketplace",
        "--limit", "50"
    ])
    print(output1)

    print("\n[*] Rotating Tor circuit...")
    new_tor_identity()
    time.sleep(3)
    print("[✓] Circuit rotated\n")

    print("━━━ PHASE 2: FINANCIAL INTEL SEARCH ━━━")
    output2 = run_spider([
        "darkweb", "--keywords",
        "credit card dumps,paypal hacked,bank account login,fullz ssn dob,cvv shop",
        "--limit", "50"
    ])
    print(output2)

    print("\n━━━ RESULT FILES ━━━")
    results_dir = os.path.join(DEEP_SPIDER, "results")
    files = sorted(
        [f for f in os.listdir(results_dir) if f.endswith(".json")],
        key=lambda f: os.path.getmtime(os.path.join(results_dir, f)), reverse=True
    )
    for f in files[:10]:
        fp = os.path.join(results_dir, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%H:%M")
        size = os.path.getsize(fp)
        print(f"  {mtime}  {size:>6}B  {f}")

    print("\n━━━ SWEEP COMPLETE ━━━")


if __name__ == "__main__":
    main()
