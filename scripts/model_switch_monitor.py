#!/usr/bin/env python3
"""
OmniRoute Model Switch Monitor — watches for provider/model changes
and sends a short Discord notification when OmniRoute switches tiers.

Usage: python model_switch_monitor.py [--daemon]

The monitor tails OmniRoute's development log and detects when the
active model/provider changes, indicating a tier fallback or promotion.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration
OMNIROUTE_LOG = Path.home() / "OmniRoute" / ".build" / "next" / "dev" / "logs" / "next-development.log"
STATE_FILE = Path.home() / "AppData/Local/hermes" / ".model_switch_state.json"

# Model tier definitions (matching the configured combo)
MODEL_TIERS = {
    "oc/deepseek-v4-flash-free": {
        "tier": 1,
        "name": "OpenCode Zen",
        "cost": "FREE",
        "quality": "DeepSeek V4 Flash"
    },
    "oc/mimo-v2.5-free": {
        "tier": 1,
        "name": "OpenCode Zen",
        "cost": "FREE",
        "quality": "Mimo 2.5"
    },
    "tllm/together_deepseek_v3": {
        "tier": 2,
        "name": "Together AI",
        "cost": "FREE",
        "quality": "DeepSeek V3"
    },
    "auto/coding:free": {
        "tier": 3,
        "name": "OmniRoute Auto-Free",
        "cost": "FREE",
        "quality": "Best Free Coding"
    },
}

# Discord webhook via Hermes (sends to home channel)
def send_notification(message: str):
    """Send notification through Hermes gateway."""
    try:
        subprocess.run(
            ["python", "-m", "hermes_cli.main", "-z", f"Send this to my home channel: {message}"],
            capture_output=True,
            text=True,
            timeout=30
        )
    except Exception as e:
        print(f"Notification send error: {e}")

def detect_model_switch(log_line: str) -> dict | None:
    """Parse OmniRoute log line for model routing decisions."""
    # Try parsing as JSON log entry
    msg = log_line
    if log_line.strip().startswith("{"):
        try:
            entry = json.loads(log_line)
            msg = entry.get("message", log_line)
        except:
            pass
    
    # Pattern: [COMBO] routing to specific model
    m = re.search(r'\[COMBO.*?\]\s+Rout(?:ing|ed)\s+(?:request\s+)?to\s+(\S+)', msg, re.IGNORECASE)
    if m:
        return {"model": m.group(1)}
    
    # Pattern: [AUTO] matched no connected models (provider exhaustion)
    m = re.search(r'\[AUTO\]\s+(\S+)\s+matched no connected', msg)
    if m:
        return {"model": m.group(1), "failed": True}
    
    # Pattern: [AUTO] routing to model
    m = re.search(r'\[AUTO.*?\]\s+(?:routed|selected|using|switched\s+to)\s+(\S+)', msg, re.IGNORECASE)
    if m:
        return {"model": m.group(1)}
    
    # Pattern: "model":"modelname" in messages
    m = re.search(r'model["\':]\s*["\']([a-zA-Z0-9_/.-]+)["\']', msg)
    if m:
        model = m.group(1)
        if any(x in model for x in ["deepseek", "qwen", "gemini", "claude", "gpt", "silicon", "mistral"]):
            return {"model": model}
    
    # Pattern: selected provider
    m = re.search(r'selected\s+(?:provider|model)[:\s]+(\S+)', msg, re.IGNORECASE)
    if m:
        return {"model": m.group(1)}
    
    return None

def get_current_state() -> str:
    """Read the last known active model from state file."""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return data.get("active_model", "unknown")
        except:
            pass
    return "unknown"

def save_current_state(model: str):
    """Save the current active model to state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "active_model": model,
        "last_updated": datetime.now().isoformat()
    }))

def monitor_log_file():
    """Tail OmniRoute log file and detect model switches."""
    log_path = OMNIROUTE_LOG
    last_model = get_current_state()
    
    print(f"📡 Model Switch Monitor Started")
    print(f"   Watching: {log_path}")
    print(f"   Current: {last_model}")
    print()
    
    # Ensure log file exists
    if not log_path.exists():
        print(f"⚠️  Log file not found: {log_path}")
        print("   Touch it to create: type nul > .build\\next\\dev\\logs\\next-development.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("")
    
    # Tail the log file
    last_size = log_path.stat().st_size
    
    try:
        while True:
            current_size = log_path.stat().st_size
            
            if current_size < last_size:
                # File was rotated
                last_size = 0
            
            if current_size > last_size:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_size)
                    for line in f:
                        line = line.strip()
                        detection = detect_model_switch(line)
                        
                        if detection:
                            model_id = detection.get("model", "")
                            tier_info = MODEL_TIERS.get(model_id, {
                                "tier": 0,
                                "name": model_id,
                                "cost": "UNKNOWN",
                                "quality": "?"
                            })
                            
                            if detection.get("failed"):
                                # Provider exhausted - will fall back
                                msg = f"→ {tier_info['quality']} exhausted"
                                print(f"   {msg}")
                                send_notification(msg)
                            elif model_id != last_model and last_model != "unknown":
                                # Model switch detected
                                arrow = "↑" if tier_info.get("tier", 99) < MODEL_TIERS.get(last_model, {}).get("tier", 0) else "↓"
                                msg = f"{arrow} {tier_info['quality']}"
                                print(f"   {msg}")
                                send_notification(msg)
                            
                            last_model = model_id
                            save_current_state(model_id)
                
                last_size = current_size
            
            time.sleep(2)  # Check every 2 seconds
    
    except KeyboardInterrupt:
        print("\nMonitor stopped.")

def main():
    parser = argparse.ArgumentParser(description="OmniRoute Model Switch Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    
    args = parser.parse_args()
    
    if args.daemon:
        monitor_log_file()
    else:
        # One-shot check
        log_path = OMNIROUTE_LOG
        if log_path.exists():
            current = get_current_state()
            print(f"Current model: {current}")
        else:
            print("OmniRoute not running yet")

if __name__ == "__main__":
    if "--daemon" in sys.argv or "-d" in sys.argv:
        main()
    else:
        # Show current state
        current = get_current_state()
        print(f"Current model: {current}")
