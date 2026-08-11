# Discord Voice Message Transcription

When the operator sends a voice message via Discord that can't be read as text.

## How the pipeline works

- Inbound audio attachments are cached to `~/AppData/Local/hermes/audio_cache/audio_<hash>.ogg` by the gateway (they persist for months — check there first).
- The agent receives the cached path as a media URL on the triggering message. If the turn arrived with a real attachment, transcribe that path directly.
- In `[Recent channel messages]` history backfill, any message whose content is empty but has attachments renders as literal text `(attachment)` — no URL, no file. That is a backfill placeholder, NOT a usable reference.

## Recovery Steps

1. **Find the most recent audio file:**
   ```bash
   ls -lt --time-style=full-iso ~/AppData/Local/hermes/audio_cache/*.ogg | head -5
   ```

2. **Transcribe with Whisper — use SYSTEM Python, not the Hermes venv.**
   The Hermes venv python (`hermes-agent/venv/Scripts/python.exe`) does NOT have whisper installed; `import whisper` fails there. System Python 3.11 has openai-whisper, faster-whisper, and whisperx:
   ```bash
   ${USER_HOME}/AppData/Local/Programs/Python/Python311/python.exe -c "
   import whisper
   model = whisper.load_model('base')
   result = model.transcribe(r'${USER_HOME}\AppData\Local\hermes\audio_cache\<file>.ogg')
   print(result['text'])
   "
   ```
   Expect a harmless `FP16 is not supported on CPU` warning. Minor transcription artifacts are normal (e.g. "cron job" → "crime job"); use conversation context to resolve intent.

## Case: message arrived as "(attachment)" with no file

If the newest cache file predates the message, the audio was never downloaded. Most common cause: **the gateway was down or restarting when the message was sent** (updates, `gateway install`, crashes). Discord does NOT replay missed gateway events — the attachment is unrecoverable. Confirm timing by decoding the Discord snowflake:

```python
msg_id = <discord-channel-id>
ts_ms = (msg_id >> 22) + 1420070400000   # Discord epoch
from datetime import datetime
print(datetime.fromtimestamp(ts_ms / 1000))  # compare against gateway restart times in logs
```

Cross-reference with `config.yaml.bak.<timestamp>` files and `update.log` mtimes — if the message landed mid-update, that's the cause. Tell the user to re-send; do not claim you heard it.

## Finding a specific message ID in logs

```bash
grep -l "<msg_id>" ~/AppData/Local/hermes/logs/*.log
grep -B2 -A8 "<msg_id>" ~/AppData/Local/hermes/logs/gateway.log
```

Inbound messages are logged as `inbound message: platform=discord user=... msg='...'`. If the voice message has no `inbound message` line, the gateway never received it.

## Requirements

- Whisper in system Python (`pip install openai-whisper` on Python 3.11)
- Model file downloads on first use (~75MB tiny, ~150MB base)
