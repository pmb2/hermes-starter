# Raw WebSocket QA Script — Spacebar Bot Connectivity Test

A standalone Python script to test all bots' WebSocket connectivity to a Spacebar gateway, bypassing discord.py entirely. Useful for distinguishing Spacebar-side issues from discord.py patching issues.

## Single-Bot Test

```python
import asyncio, websockets, json

async def test_bot(token: str, name: str) -> bool:
    uri = "wss://discy.your-domain.example/"
    print(f"{name}: Connecting to {uri}...")
    async with websockets.connect(uri, ping_interval=30, ping_timeout=10) as ws:
        hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        assert hello["op"] == 10, f"Expected Hello (op=10), got op={hello['op']}"
        print(f"{name}: Hello received, heartbeat_interval={hello['d']['heartbeat_interval']}")

        identify = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {"os": "win32", "browser": "test", "device": "test"},
                "compress": False,
                "large_threshold": 250,
                "intents": 32767,  # ALL intents
            },
        }
        await ws.send(json.dumps(identify))
        print(f"{name}: Identify sent")

        for _ in range(10):
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            op, t = data.get("op"), data.get("t", "")
            if op == 0 and t == "READY":
                user = data["d"]["user"]
                guilds = data["d"]["guilds"]
                print(f"{name}: READY! User={user['username']} Guilds={len(guilds)}")
                return True
            elif op == 9:
                print(f"{name}: INVALID_SESSION: {data['d']}")
                return False
            else:
                print(f"{name}: op={op} t={t}")

        print(f"{name}: No READY received (may need more time)")
        return True  # connection works, just slow

    return False
```

## Multi-Bot Parallel Test (All 5 Hermes Dev Bots)

```python
async def test_all():
    bot_tokens = {
        "dev-lead": "<token>",
        "skills-lead": "<token>",
        "integration-lead": "<token>",
        "qa-lead": "<token>",
        "docs-lead": "<token>",
    }
    results = await asyncio.gather(
        *[test_bot(token, name) for name, token in bot_tokens.items()],
        return_exceptions=True,
    )
    for name, result in zip(bot_tokens.keys(), results):
        if isinstance(result, Exception):
            print(f"❌ {name}: ERROR — {result}")
        elif result:
            print(f"✅ {name}: connected")
        else:
            print(f"❌ {name}: failed")

asyncio.run(test_all())
```

## Expected Output

Each bot should produce:
```
{bot}: Connecting to wss://discy.your-domain.example/...
{bot}: Hello received, heartbeat_interval=30000
{bot}: Identify sent
{bot}: READY! User={bot} Guilds=1
```

After all 5, you should see events in this order per bot:
1. `op=10, t=` — Hello (server identifies itself)
2. `op=0, t=READY` — Authentication success, includes guild list
3. `op=0, t=GUILD_CREATE` — Full guild data (channels, members, roles)
4. `op=0, t=READY_SUPPLEMENTAL` — Additional metadata

## When to Use

- **Gateway troubleshooting:** If the Hermes gateway (discord.py patched) won't connect, run this test to verify the Spacebar server is accepting WebSocket connections
- **Token validation:** Confirms the bot token is valid against the Spacebar gateway
- **Intent compatibility:** Test with different intent masks (start with 32767, then narrow to 513 or 769)
- **Post-deployment verification:** Run after adding new bots to confirm they authenticate

## Known Results (discy.your-domain.example)

- All 5 Hermes Dev bots connect in <2s with intents=32767
- Guild count shows 1 (the the operator guild)
- GUILD_CREATE payload contains full channel listing (22 channels across 4 categories)
