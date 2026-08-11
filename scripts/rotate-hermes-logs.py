#!/usr/bin/env python3
"""Rotate oversized Hermes log files safely (truncate after archive).

Designed for no_agent cron. Never deletes without gzip archive on E:.
"""
from __future__ import annotations

import gzip
import shutil
import time
from pathlib import Path

HERMES = Path.home() / "AppData" / "Local" / "hermes"
LOG_DIR = HERMES / "logs"
ARCH = Path(r"${MY_REPOS}\Archives\hermes\logs\rotated")
# Rotate when larger than this
MAX_BYTES = 200 * 1024 * 1024  # 200 MB
# Always watch these first
WATCH = [
    LOG_DIR / "mcp-stderr.log",
    LOG_DIR / "gateway-stdio.log",
    HERMES / "gateway-stderr.log",
]


def archive_and_truncate(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return f"skip missing {path.name}"
    size = path.stat().st_size
    if size < MAX_BYTES:
        return f"ok {path.name} {size/1024/1024:.1f}MB"
    ARCH.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = ARCH / f"{path.name}.{stamp}.gz"
    with open(path, "rb") as src, gzip.open(dest, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    # Truncate in place so open writers keep the same path
    with open(path, "wb"):
        pass
    return f"rotated {path.name} {size/1024/1024:.1f}MB -> {dest.name} ({dest.stat().st_size/1024/1024:.1f}MB gz)"


def main() -> int:
    results = [archive_and_truncate(p) for p in WATCH]
    # Also any other *.log under logs/ over limit
    if LOG_DIR.exists():
        for p in LOG_DIR.glob("*.log"):
            if p not in WATCH and p.stat().st_size >= MAX_BYTES:
                results.append(archive_and_truncate(p))
    print("Hermes log rotate:", time.strftime("%Y-%m-%d %H:%M:%S"))
    for r in results:
        print(" ", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
