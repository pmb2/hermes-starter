#!/usr/bin/env python3
"""
Telegram Search via MTProto (Telethon) — routes through Tor SOCKS5
No web scraping needed — uses Telegram's native API.

SETUP:
  1. Get API credentials at https://my.telegram.org/apps
  2. Create a Telegram account with a burner number (Google Voice works)
  3. First run will prompt for phone + code

Usage:
  python tg_searcher.py --keywords "stealer logs,credentials,dumps"
  python tg_searcher.py --keywords "breach data" --channels-only
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime

RESULTS_DIR = os.path.expanduser("~/deep-spider/results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SESSION_FILE = os.path.expanduser("~/deep-spider/tg_session")


def search_telegram_mtproto(keywords, max_results=100, channels_only=False):
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")

    if not api_id or not api_hash:
        print("=" * 60)
        print("TELEGRAM API CREDENTIALS REQUIRED")
        print("=" * 60)
        print("Set environment variables:")
        print("  TG_API_ID=<your_api_id>")
        print("  TG_API_HASH=<your_api_hash>")
        print()
        print("Get them at: https://my.telegram.org/apps")
        print("=" * 60)
        return []

    from telethon import TelegramClient, functions, types
    from telethon.errors import SessionPasswordNeededError

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to Telegram via Tor...")

    client = TelegramClient(
        SESSION_FILE,
        int(api_id),
        api_hash,
        proxy=("socks5", "127.0.0.1", 9050)
    )

    try:
        client.start()
        me = client.get_me()
        print(f"  Authenticated as @{me.username or me.phone or me.id}")
    except SessionPasswordNeededError:
        print("  Two-factor auth required. Enter your password:")
        password = input("> ")
        client.start(password=password)
    except Exception as e:
        print(f"  Auth error: {e}")
        print("  Delete ~/deep-spider/tg_session and re-run for fresh auth")
        return []

    kw_list = [k.strip() for k in keywords.split(",")]
    all_results = []
    seen_ids = set()

    for kw in kw_list[:5]:
        print(f"  Searching Telegram for: {kw}")
        try:
            if channels_only:
                result = client(functions.contacts.SearchRequest(
                    q=kw, limit=min(30, max_results)
                ))
                for chat in getattr(result, "chats", result if isinstance(result, list) else []):
                    if hasattr(chat, "id") and chat.id not in seen_ids:
                        seen_ids.add(chat.id)
                        title = getattr(chat, "title", "") or getattr(chat, "username", "") or ""
                        username = getattr(chat, "username", "") or ""
                        link = f"https://t.me/{username}" if username else f"tg://openmessage?chat_id={chat.id}"
                        members = getattr(chat, "participants_count", "?")
                        all_results.append({
                            "type": "channel", "keyword": kw,
                            "title": title, "username": username,
                            "url": link, "members": members, "id": chat.id
                        })
                        print(f"    Channel: {title} (@{username}) — {members} members")
            else:
                result = client(functions.messages.SearchGlobalRequest(
                    q=kw, limit=min(30, max_results),
                    filter=types.InputMessagesFilterEmpty()
                ))
                for msg in getattr(result, "messages", result if isinstance(result, list) else []):
                    if hasattr(msg, "id") and msg.id not in seen_ids:
                        seen_ids.add(msg.id)
                        chat_title = ""
                        chat_link = ""
                        peer = getattr(msg, "peer_id", None)
                        if peer:
                            try:
                                entity = client.get_entity(peer)
                                chat_title = getattr(entity, "title", "") or getattr(entity, "username", "") or ""
                                username = getattr(entity, "username", "")
                                chat_link = f"https://t.me/{username}/{msg.id}" if username else ""
                            except:
                                pass
                        text = getattr(msg, "message", "") or ""
                        all_results.append({
                            "type": "message", "keyword": kw,
                            "chat": chat_title, "url": chat_link,
                            "text": text[:200] if text else "",
                            "id": msg.id, "date": str(getattr(msg, "date", ""))
                        })

            print(f"    Found {len([r for r in all_results if r['keyword'] == kw])} results for '{kw}'")
            time.sleep(3)
        except Exception as e:
            print(f"    Search error: {e}")

    client.disconnect()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    kw_slug = re.sub(r'[^a-z0-9]+', '_', keywords.lower())[:40]
    path = os.path.join(RESULTS_DIR, f"tg_mtproto_{kw_slug}_{ts}.json")
    with open(path, "w") as f:
        json.dump({"source": "telegram_mtproto", "keywords": keywords,
                    "timestamp": ts, "count": len(all_results),
                    "results": all_results}, f, indent=2)
    print(f"\nSaved {len(all_results)} results → {path}")

    print(f"\n{'=' * 60}\nTELEGRAM RESULTS: {len(all_results)} hits\n{'=' * 60}")
    for r in all_results[:20]:
        if r["type"] == "channel":
            print(f"  📢 @{r['username']} — {r['title']}\n     {r['url']}  ({r['members']} members)")
        else:
            print(f"  💬 {r['chat']}: {r['text'][:100]}")
            if r['url']:
                print(f"     {r['url']}")
    if len(all_results) > 20:
        print(f"  ... and {len(all_results) - 20} more")

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram Search via MTProto (Tor)")
    parser.add_argument("--keywords", "-k", required=True)
    parser.add_argument("--channels-only", action="store_true")
    parser.add_argument("--limit", "-l", type=int, default=100)
    args = parser.parse_args()

    if args.channels_only:
        search_telegram_mtproto(args.keywords, args.limit, channels_only=True)
    else:
        search_telegram_mtproto(args.keywords, args.limit)
