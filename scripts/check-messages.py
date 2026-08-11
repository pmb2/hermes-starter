#!/usr/bin/env python3
"""Check gateway message flow - search logs for message events"""
import os
from pathlib import Path

logs_dir = Path.home() / ".hermes/logs"
profile = "chief-of-staff"
logfile = logs_dir / f"spacebar-{profile}.log"

if logfile.exists():
    content = logfile.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    print(f"Log: {logfile} ({len(lines)} lines)")
    
    # Find any message-related, error, or allow/deny entries
    for line in lines:
        low = line.lower()
        if any(kw in low for kw in ["message", "on_message", "allow", "deny", "filter", 
                                     "error", "traceback", "exception", "crash",
                                     "typing", "received", "respond"]):
            print(f"  {line[:200]}")
    
    # Count lines by type
    msg_count = sum(1 for l in lines if "message" in l.lower())
    err_count = sum(1 for l in lines if "error" in l.lower())
    print(f"\nMessage-related lines: {msg_count}")
    print(f"Error lines: {err_count}")
else:
    print(f"Log file not found at {logfile}")

# Check other bot logs too
print("\n=== Checking recent bot logs for errors ===")
for bot in ["technology-lead", "development-lead", "intelligence-lead"]:
    f = logs_dir / f"spacebar-{bot}.log"
    if f.exists():
        c = f.read_text(encoding="utf-8", errors="replace")
        if "error" in c.lower() or "traceback" in c.lower():
            print(f"{bot}: HAS ERRORS")
        else:
            print(f"{bot}: OK (no errors)")
