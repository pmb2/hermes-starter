---
name: voice-memo-transcription
description: "Transcribe Discord voice memos and other audio attachments with local Whisper. Covers the Hermes audio_cache location, finding the latest attachment, the system-Python-vs-venv whisper trap, and delivering transcripts with artifact notes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [audio, transcription, whisper, discord, voice-memo, ogg]
    triggers: [transcribe-audio, voice-memo, audio-attachment, transcribe-this, what-did-i-say, voice-note]
    related_skills: [songsee, youtube]
---

# Voice Memo Transcription

Transcribe Discord voice memos / audio attachments the operator sends, using local Whisper. No API key needed — runs on CPU.

## Where Attachments Land

Discord voice memos and audio attachments are cached by the gateway at:

```
~/AppData/Local/hermes/audio_cache/*.ogg
```

Find the most recent one:

```bash
ls -lt --time-style=full-iso ~/AppData/Local/hermes/audio_cache/ | head -3
```

**Check mtime against when the user says they sent it.** If the newest cached file is hours old and the user just sent an attachment, the new one hasn't downloaded — transcribe the newest available and note that a fresher attachment may not have arrived, inviting a re-send.

## The Python Trap (important)

`import whisper` FAILS in the default `python` (Hermes venv at `~/AppData/Local/hermes/hermes-agent/venv/`). Whisper lives in the **system Python 3.11** site-packages. Invoke it by absolute path:

```bash
${USER_HOME}/AppData/Local/Programs/Python/Python311/python.exe -c "
import whisper
model = whisper.load_model('base')
result = model.transcribe('audio_XXXXXXXX.ogg')
print(result['text'])
"
```

Installed in system Python 3.11: `openai-whisper` (20240930), `faster-whisper` (1.2.1), `whisperx` (3.8.6), `whispercpp`. All run from `${USER_HOME}\AppData\Local\Programs\Python\Python311\`.

## Model Choice

- `base` — fast, fine for short memos. Transcription artifacts on casual speech are normal (observed: "cron job" → "crime job", "locations" → "patients").
- `small` / `medium` — better accuracy, slower on CPU. Use when the memo is long or the base output is garbled.
- The `FP16 is not supported on CPU; using FP32 instead` warning is cosmetic — ignore it.

## Delivery Format

1. Quote the transcript in full, in a blockquote.
2. Note likely Whisper artifacts in italics with the probable intended words — context usually makes intent obvious.
3. State which file was transcribed (name + mtime).
4. If the transcript matches a request already handled in the session, say so and point at the work — don't redo it.

## Pitfalls

- **Don't guess which file** — always `ls -lt` first. Cache holds many old memos.
- **`type` doesn't exist in git-bash** — use `cat`/`head`/`grep` for file inspection on this Windows host.
- **faster-whisper import name** is `faster_whisper` (underscore), but it's in the same system Python — same invocation pattern works.
- **Long memos**: transcription of multi-minute audio on CPU can take minutes. Use `timeout=300` on the terminal call and run in foreground — it returns when done.
