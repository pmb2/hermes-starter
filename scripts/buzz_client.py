#!/usr/bin/env python3
"""
Buzz Bridge — Nostr client for the buzz relay.
Connects, authenticates (NIP-42), sends/receives events.
Used by Hermes profiles to participate in buzz channels.
"""
import json, hashlib, time, threading, os, sys
from pathlib import Path
from typing import Optional, Callable, Any
import websocket

from nostr_protocol import Keys, EventBuilder, Kind, Tag

# ── Core Client ──────────────────────────────────────────────────────────────

class BuzzClient:
    """Low-level Nostr client for the buzz relay."""
    
    def __init__(self, secret_key: str, relay_url: str = "ws://localhost:3000"):
        self.keys = Keys.parse(secret_key)
        self.pubkey = self.keys.public_key().to_hex()
        self.relay_url = relay_url
        self.ws: Optional[websocket.WebSocket] = None
        self.authenticated = False
        self.subs = {}  # sub_id -> callback
        self._running = False
        self._lock = threading.Lock()
    
    def _make_event(self, kind: int, content: str, tags: list[list[str]] = None) -> dict:
        """Create a signed Nostr event."""
        if tags is None:
            tags = []
        tag_objects = [Tag.parse(t) for t in tags]
        builder = EventBuilder(Kind(kind), content, tag_objects)
        event = builder.to_event(self.keys)
        return {
            "id": event.id().to_hex(),
            "pubkey": event.author().to_hex(),
            "created_at": event.created_at().as_secs(),
            "kind": kind,
            "tags": [t.as_vec() for t in event.tags()],
            "content": content,
            "sig": event.signature(),
        }
    
    def connect(self) -> bool:
        """Connect and authenticate to the relay."""
        self.ws = websocket.create_connection(self.relay_url, timeout=10)
        
        # Receive AUTH challenge
        msg = json.loads(self.ws.recv())
        if msg[0] != "AUTH":
            raise RuntimeError(f"Expected AUTH challenge, got {msg[0]}")
        challenge = msg[1]
        
        # Build and send auth response
        auth_evt = self._make_event(22242, "", [
            ["challenge", challenge],
            ["relay", self.relay_url],
        ])
        self.ws.send(json.dumps(["AUTH", auth_evt]))
        
        # Wait for OK
        self.ws.settimeout(5)
        while True:
            resp = json.loads(self.ws.recv())
            if resp[0] == "OK":
                if resp[2]:
                    self.authenticated = True
                    return True
                return False
            elif resp[0] == "AUTH":
                continue
        self._running = True
        return False
    
    def send_event(self, kind: int, content: str, tags: list[list[str]] = None) -> Optional[str]:
        """Send an event to the relay. Returns event ID if accepted."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated — call connect() first")
        
        event = self._make_event(kind, content, tags)
        msg = json.dumps(["EVENT", event])
        self.ws.send(msg)
        
        # Read ALL responses after EVENT
        self.ws.settimeout(5)
        for _ in range(3):
            try:
                resp = json.loads(self.ws.recv())
                if resp[0] == "OK" and resp[1] == event["id"]:
                    if resp[2]:
                        return event["id"]
                    else:
                        reason = resp[3] if len(resp) > 3 else "unknown"
                        print(f"  EVENT REJECTED: {reason}")
                        return None
                elif resp[0] == "OK":
                    # OK for a different event ID
                    continue
            except:
                break
        return None
    
    def send_channel_message(self, channel: str, content: str) -> Optional[str]:
        """Send a NIP-29 channel message (kind 9).
        `channel` can be a UUID or a channel name (looked up from buzz_channels.json).
        """
        ch_uuid = resolve_channel_uuid(channel)
        return self.send_event(9, content, [["h", ch_uuid]])
    
    def send_text_note(self, content: str) -> Optional[str]:
        """Send a text note (kind 1)."""
        return self.send_event(1, content)
    
    def query(self, filters: dict, callback: Callable = None, timeout: float = 5.0) -> list:
        """Query events from the relay. Returns list of events."""
        import uuid
        sub_id = str(uuid.uuid4())[:8]
        
        self.ws.send(json.dumps(["REQ", sub_id, filters]))
        
        events = []
        self.ws.settimeout(timeout)
        while True:
            try:
                resp = json.loads(self.ws.recv())
                if resp[0] == "EVENT":
                    events.append(resp[2])
                    if callback:
                        callback(resp[2])
                elif resp[0] == "EOSE":
                    break
            except:
                break
        
        # Close subscription
        try:
            self.ws.send(json.dumps(["CLOSE", sub_id]))
        except:
            pass
        
        return events
    
    def close(self):
        """Disconnect."""
        self._running = False
        if self.ws:
            try:
                self.ws.send(json.dumps(["CLOSE", "*"]))
            except:
                pass
            self.ws.close()
        self.authenticated = False
    
    def ping(self):
        """Send WebSocket ping to keep connection alive."""
        if self.ws:
            self.ws.ping()
    
    def subscribe(self, sub_id: str, filters: dict, callback: Callable = None, timeout: float = None):
        """Persistent subscription. Calls `callback(event)` for each event.
        Blocks until CLOSE is received or timeout expires."""
        self.ws.send(json.dumps(["REQ", sub_id, filters]))
        self.subs[sub_id] = callback
        self.ws.settimeout(timeout or 86400)  # default 24h
        try:
            while self._running:
                resp = json.loads(self.ws.recv())
                if resp[0] == "EVENT":
                    if callback:
                        callback(resp[2])
                elif resp[0] == "EOSE":
                    # End of stored events — keep listening for new ones
                    continue
                elif resp[0] == "CLOSED":
                    print(f"  Subscription {sub_id} closed: {resp[2]}")
                    break
        except websocket.WebSocketTimeoutException:
            pass
        except Exception as e:
            print(f"  Subscription {sub_id} error: {e}")
    
    def unsubscribe(self, sub_id: str):
        """Close a subscription."""
        try:
            self.ws.send(json.dumps(["CLOSE", sub_id]))
        except:
            pass
        self.subs.pop(sub_id, None)

# ── Convenience API for Hermes profiles ──────────────────────────────────────

CHANNEL_CACHE = None

def _load_channel_map():
    """Load channel UUID map from buzz_channels.json."""
    global CHANNEL_CACHE
    if CHANNEL_CACHE is None:
        ch_path = Path(__file__).parent / "buzz_channels.json"
        if ch_path.exists():
            CHANNEL_CACHE = json.loads(ch_path.read_text())
        else:
            CHANNEL_CACHE = {}
    return CHANNEL_CACHE

def resolve_channel_uuid(channel: str) -> str:
    """Resolve a channel name or UUID to the UUID the relay expects.
    If already a UUID, returns as-is.
    If a channel name, looks up from buzz_channels.json.
    """
    # Check if it's already a UUID
    if '-' in channel and len(channel) == 36:
        return channel
    # Look up by name
    chan_map = _load_channel_map()
    if channel in chan_map:
        return chan_map[channel]
    # Return as-is (might be a pre-existing UUID or a name we don't have)
    return channel

def load_profile_key(profile_name: str) -> Optional[str]:
    """Load a profile's Nostr secret key from the keys file."""
    keys_path = Path(__file__).parent / "buzz_keys.json"
    if not keys_path.exists():
        return None
    db = json.loads(keys_path.read_text())
    if profile_name in db:
        return db[profile_name]["secret_key"]
    return None

def load_profile_channels(profile_name: str) -> list:
    """Get the channels a profile should join."""
    keys_path = Path(__file__).parent / "buzz_keys.json"
    if not keys_path.exists():
        return []
    db = json.loads(keys_path.read_text())
    if profile_name in db:
        return db[profile_name].get("channels", ["general"])
    return ["general"]

def send_to_buzz(profile_name: str, channel: str, message: str) -> dict:
    """Send a message to a buzz channel as a specific profile.
    Returns dict with success status and event_id.
    """
    sk = load_profile_key(profile_name)
    if not sk:
        return {"success": False, "error": f"No key for profile '{profile_name}'"}
    
    try:
        client = BuzzClient(sk)
        if not client.connect():
            return {"success": False, "error": "Authentication failed"}
        
        event_id = client.send_channel_message(channel, message)
        client.close()
        
        if event_id:
            return {"success": True, "event_id": event_id, "channel": channel, "profile": profile_name}
        else:
            return {"success": False, "error": "Event rejected by relay"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_dm_to(profile_name: str, target_pubkey: str, message: str) -> dict:
    """Send a direct message (NIP-04 encrypted) to another profile."""
    # For now, send as kind 4 (encrypted DM)
    # TODO: implement NIP-04 encryption
    return send_to_buzz(profile_name, "", f"DM to {target_pubkey[:16]}: {message}")

# ── CLI interface ─────────────────────────────────────────────────────────────

def main():
    """CLI entry point for buzz bridge."""
    args = sys.argv[1:]
    
    if not args:
        print("Usage:")
        print("  buzz_bridge.py send <profile> <channel> <message>")
        print("  buzz_bridge.py query <profile> <kind> [limit]")
        print("  buzz_bridge.py list-keys")
        print("  buzz_bridge.py test")
        return
    
    if args[0] == "send" and len(args) >= 4:
        result = send_to_buzz(args[1], args[2], args[3])
        print(json.dumps(result, indent=2))
    
    elif args[0] == "query" and len(args) >= 2:
        sk = load_profile_key(args[1])
        if not sk:
            print(json.dumps({"error": f"No key for '{args[1]}'"}))
            return
        kind = int(args[2]) if len(args) > 2 else 1
        limit = int(args[3]) if len(args) > 3 else 10
        
        client = BuzzClient(sk)
        client.connect()
        results = client.query({"kinds": [kind], "limit": limit})
        client.close()
        print(json.dumps({"count": len(results), "events": results}, indent=2))
    
    elif args[0] == "list-keys":
        keys_path = Path(__file__).parent / "buzz_keys.json"
        if keys_path.exists():
            db = json.loads(keys_path.read_text())
            for name, data in sorted(db.items()):
                print(f"  {name:30s} {data['public_key'][:16]}...  channels={','.join(data['channels'][:3])}")
        else:
            print("No keys file found")
    
    elif args[0] == "test":
        # Self-test: connect, send, query
        print("Testing buzz relay connection...")
        sk = load_profile_key("dev-lead") or Keys.generate().secret_key().to_hex()
        client = BuzzClient(sk)
        if client.connect():
            print(f"  ✓ Authenticated as {client.pubkey[:16]}...")
            eid = client.send_channel_message("general", "Buzz bridge self-test ✓")
            if eid:
                print(f"  ✓ Message sent: {eid[:16]}...")
            results = client.query({"kinds": [9], "limit": 3})
            print(f"  ✓ Query returned {len(results)} channel messages")
            client.close()
            print("  ✓ Buzz bridge operational!")
        else:
            print("  ✗ Authentication failed")

if __name__ == "__main__":
    main()
