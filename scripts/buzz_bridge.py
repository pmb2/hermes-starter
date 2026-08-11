#!/usr/bin/env python3
"""Buzz bridge utility — Nostr key generation, signing, and relay interaction."""
import json, sys, os, time, hashlib, hmac
from pathlib import Path
from nostr_protocol import Keys, EventBuilder, Tag, Kind, Timestamp, Event

def generate_nostr_key(name="unnamed"):
    """Generate a Nostr keypair and return structured data."""
    keys = Keys.generate()
    return {
        "name": name,
        "secret_key": keys.secret_key().to_hex(),
        "public_key": keys.public_key().to_hex(),
        "public_key_bech32": keys.public_key().to_bech32(),
    }

def create_event(keys, kind=1, content="", tags=None, channel=""):
    """Create and sign a Nostr event."""
    if tags is None:
        tags = []
    if channel:
        # NIP-29 channel message uses 'h' tag
        tags = [["h", channel]] + tags
    builder = EventBuilder(Kind(kind), content, [Tag(t) for t in tags])
    event = builder.to_event(keys)
    return event

def event_to_dict(event):
    """Convert a signed event to JSON-serializable dict."""
    return {
        "id": event.id().to_hex(),
        "pubkey": event.author().to_hex(),
        "created_at": event.created_at().as_secs(),
        "kind": event.kind().as_u16(),
        "tags": [t.as_vec() for t in event.tags()],
        "content": event.content(),
        "sig": event.signature(),
    }

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if action == "keygen":
        name = sys.argv[2] if len(sys.argv) > 2 else "agent"
        key = generate_nostr_key(name)
        print(json.dumps(key, indent=2))
        
    elif action == "sign":
        # Sign a message: sign <secret_key_hex> <kind> <content>
        sk_hex = sys.argv[2]
        kind = int(sys.argv[3])
        content = sys.argv[4]
        channel = sys.argv[5] if len(sys.argv) > 5 else ""
        
        keys = Keys.from_sk(sk_hex)
        event = create_event(keys, kind=kind, content=content, channel=channel)
        print(json.dumps(event_to_dict(event), indent=2))
        
    elif action == "event-json":
        # Create event JSON from stdin or args
        sk_hex = sys.argv[2]
        kind = int(sys.argv[3])
        content = sys.argv[4]
        channel = sys.argv[5] if len(sys.argv) > 5 else ""
        
        keys = Keys.from_sk(sk_hex)
        event = create_event(keys, kind=kind, content=content, channel=channel)
        sys.stdout.write(json.dumps(event_to_dict(event)) + "\n")
        
    elif action == "batch-keygen":
        names = sys.argv[2:]
        keys_list = []
        for name in names:
            keys_list.append(generate_nostr_key(name))
        print(json.dumps(keys_list, indent=2))
        
    else:
        print(f"Usage: {sys.argv[0]} <action> [args]")
        print("  keygen <name>               — Generate single Nostr key")
        print("  batch-keygen <name1> <n2>... — Generate multiple keys")
        print("  sign <sk> <kind> <content>     — Sign and output event JSON")

if __name__ == "__main__":
    main()
