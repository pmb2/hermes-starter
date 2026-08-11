#!/usr/bin/env python3
"""
slow-roll-proxy — Organic Traffic Engine (osint-redteam script)

Usage:
  # TCP proxy mode (set http_proxy before running tools)
  python slow-roll-proxy.py --port 8080 --profile human

  # Pipe wrapper mode
  cat targets.txt | python slow-roll-proxy.py --wrap "httpx -tech-detect -json"

Profiles:
  human      → jitter 15±5s,  4/min, Tor routing
  researcher → jitter  5±2s, 10/min, Tor routing
  bot        → jitter  1±0.5s, 30/min, optional proxy

Full source: agent-universe/teams/07-recon-team/shared/slow-roll-proxy/proxy.py
"""

import argparse
import random
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

# ── Human-like Browser User Agents ───────────────────────────────────

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

REFERERS = [
    "https://www.google.com/search?q=",
    "https://news.ycombinator.com/",
    "https://www.reddit.com/",
    "https://github.com/",
    "https://stackoverflow.com/",
    "https://twitter.com/home",
    "",
]

class JitterTimer:
    def __init__(self, mean=15.0, stddev=5.0):
        self.mean, self.stddev = mean, stddev
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            elapsed = time.time() - self._last
            delay = max(0.5, random.gauss(self.mean, self.stddev))
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last = time.time()

class RateLimiter:
    def __init__(self, per_min=4):
        self.per_min = per_min
        self._window = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.time()
        with self._lock:
            self._window = [t for t in self._window if now - t < 60]
            if len(self._window) >= self.per_min:
                return False
            self._window.append(now)
            return True

# ── TCP Proxy Handler ────────────────────────────────────────────────

def _proxy_handle(jitter, limiter):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                data = self.rfile.readline()
                if not data: return
                line = data.decode().strip()
                parts = line.split()
                if len(parts) < 3: return
                _, url, _ = parts
                parsed = __import__("urllib.parse").urlparse(url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or (443 if parsed.scheme == "https" else 80)

                jitter.wait()
                if not limiter.allow():
                    self.wfile.write(b"HTTP/1.1 429 Too Many Requests\r\n\r\n")
                    return

                ua = random.choice(UAS)
                ref = random.choice(REFERERS)
                modified = data
                if b"User-Agent:" not in data:
                    modified += f"User-Agent: {ua}\r\n".encode()
                if ref and b"Referer:" not in data:
                    modified += f"Referer: {ref}\r\n".encode()

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.connect((host, port))
                    sock.sendall(modified)
                    while True:
                        chunk = sock.recv(4096)
                        if not chunk: break
                        self.wfile.write(chunk)
                finally:
                    sock.close()
            except Exception as e:
                print(f"[slow-roll] {e}", file=sys.stderr)
    return Handler

# ── Pipe Wrapper Mode ────────────────────────────────────────────────

def pipe_wrap(tool_cmd: str, jitter, limiter):
    for line in sys.stdin:
        target = line.strip()
        if not target: continue
        jitter.wait()
        if not limiter.allow():
            print(f"[slow-roll] rate-limited: {target}", file=sys.stderr)
            continue
        env = __import__("os").environ.copy()
        env.update({"HTTP_USER_AGENT": random.choice(UAS), "HTTP_REFERER": random.choice(REFERERS)})
        print(f"[slow-roll] → {target} via {tool_cmd.split()[0]}", file=sys.stderr)
        subprocess.run(tool_cmd.split(), env=env)

# ── CLI ──────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="slow-roll-proxy: organic traffic engine")
    ap.add_argument("--mode", choices=["proxy", "pipe"], default="proxy")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--wrap", type=str, default="")
    ap.add_argument("--profile", choices=["bot", "researcher", "human"], default="human")

    args = ap.parse_args()
    profiles = {"bot": (1, 0.5, 30), "researcher": (5, 2, 10), "human": (15, 5, 4)}
    mean, std, per_min = profiles[args.profile]
    jitter, limiter = JitterTimer(mean, std), RateLimiter(per_min)

    print(f"[slow-roll] profile={args.profile} jitter={mean}±{std}s rate={per_min}/min mode={args.mode}")

    if args.mode == "proxy":
        handler = _proxy_handle(jitter, limiter)
        srv = socketserver.ThreadingTCPServer(("0.0.0.0", args.port), handler)
        print(f"[slow-roll] TCP proxy on :{args.port}")
        srv.serve_forever()
    elif args.mode == "pipe" and args.wrap:
        pipe_wrap(args.wrap, jitter, limiter)

if __name__ == "__main__":
    main()
