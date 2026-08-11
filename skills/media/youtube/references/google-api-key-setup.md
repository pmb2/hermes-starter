# Google Gemini API Key — Setup & Extraction

For the YouTube transcript summarizer (`yt_summarize.py`) to use Google's Gemini API natively, a valid `GOOGLE_API_KEY` is required.

## Getting a Key

1. Visit https://aistudio.google.com/apikey
2. Log in with your Google account (the operator uses `<your-email>@gmail.com`)
3. Click "Create API key" if none exists, or click an existing key row to open the details dialog
4. The key is partially masked (`AIzaSy...8Lv4` or `AQ...`) in the dialog — click "Copy key" to copy the full string
5. Save it to a `.env` file or set as `GOOGLE_API_KEY` environment variable

## the operator's Key

- **Stored at:** `${MY_REPOS}/AI-Scientist/.env` as `GOOGLE_API_KEY`
- **Format:** `AQ.Ab8RN...l_LQ` (53 chars, Google Cloud "precursor" format — not the usual `AIza` prefix)
- **Project:** `projects/393747421265` (gen-lang-client-0177634060)
- **Billing:** Free tier (the "Set up billing" link is visible in AI Studio — billing hasn't been enabled)
- **Expired key found elsewhere:** `${MY_REPOS}\Documents\github\sales\receptionist\.env` had `AIzaSyBX...XiBU` which was expired

## Free Tier Limits & Model Selection

**Critical finding (May 2026):** Different Gemini models have **separate daily quota pools** on the free tier.

| Model | Quota Pool | Requests/day | Status |
|-------|-----------|-------------|--------|
| `gemini-2.5-flash-lite` | Separate pool | ~1,000 | ✅ Available when 2.0-flash quota exhausted |
| `gemini-2.0-flash` | Pool A | 1,500 | ⚠️ Exhausts quickly |
| `gemini-2.0-flash-001` | Pool A | 1,500 | ⚠️ Same pool as 2.0-flash |
| `gemini-2.0-flash-lite-001` | Pool A (?) | Not tested | May share 2.0 quota |

**If `gemini-2.0-flash` returns quota errors, try `gemini-2.5-flash-lite`** — it has its own free quota pool and won't be exhausted.

## Quota Exhaustion Recovery

When the daily free quota is exhausted (error: "429 You exceeded your current quota"):

1. **Switch to `gemini-2.5-flash-lite`** — different quota pool, often still available
2. **Use OpenRouter fallback** — `yt_summarize.py` auto-tries `nvidia/nemotron-3-nano-30b-a3b:free` when Google fails
3. **Create a new API key** — new keys get fresh quota. Visit AI Studio
4. **Set up billing** — the "Set up billing" link on the key dialog enables paid tier
5. **Wait for reset** — free tier resets at midnight PT

## Key Storage

The `yt_summarize.py` script auto-detects the key from:
1. `GOOGLE_API_KEY` environment variable
2. `.env` files in project directories
3. Hermes config at `${USER_HOME}\AppData\Local\hermes\config.yaml`

## Key Expiry & Rotation

Google AI Studio API keys can expire. An expired key returns `"API key expired."` If the summarizer fails with auth errors, check AI Studio and copy a fresh key.

## Extracting Key via BiDi Browser Automation

If the key needs to be fetched programmatically:
1. Start Firefox: `"firefox.exe" --remote-debugging-port 9222 -P "default-release-1" --no-remote`
2. Connect via WebSocket BiDi: `ws://127.0.0.1:9222/session`
3. Navigate to `https://aistudio.google.com/apikey`
4. Click the key row, then "Copy key"
5. **Limitation:** Clipboard API doesn't work in headless. Key is masked in DOM. **Easiest:** ask user to copy manually.
6. **Session limit:** BiDi only allows 1 active session per Firefox port.

## Alternative: OpenRouter Free Model Fallback

If no valid Google key is available, `--provider openrouter` uses `nvidia/nemotron-3-nano-30b-a3b:free`. Use sequential (batch_size=1) to avoid rate limits.
