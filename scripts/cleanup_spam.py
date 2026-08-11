#!/usr/bin/env python3
"""Delete spam messages from agent reply loops."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from buzz_client import BuzzClient

KEYS = json.loads((Path(__file__).parent / "buzz_keys.json").read_text())
HOSTED = "ws://localhost:3000"

for slug in KEYS:
    if slug == "the operator":
        continue
    sk = KEYS[slug].get("secret_key")
    if not sk:
        continue
    
    try:
        client = BuzzClient(sk, relay_url=HOSTED)
        client.connect()
        
        client.ws.send(json.dumps(["REQ", "scan", {
            "kinds": [9], "authors": [client.pubkey], "limit": 50
        }]))
        client.ws.settimeout(5)
        
        to_delete = []
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                r = json.loads(client.ws.recv())
                if r[0] == "EVENT":
                    content = r[2].get("content", "")
                    if "Processing" in content or "@" in content:
                        to_delete.append(r[2]["id"])
                        print(f"  {slug}: \"{content[:50]}...\"")
            except:
                break
        
        for evtid in to_delete:
            client.send_event(5, "", [["e", evtid]])
        
        if to_delete:
            print(f"  => {slug}: deleted {len(to_delete)}")
        client.close()
    except Exception as e:
        print(f"  X {slug}: {e}")

print("\nDone")
