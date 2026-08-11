# YouTube Iterative Review Workflow

## OAuth Setup (One-Time)

1. Create Google Cloud project → enable YouTube Data API v3
2. Credentials → OAuth client ID → Desktop application
3. Download `client_secret.json` → place in project root
4. First `--upload` opens a browser for consent. **If running headless/background**, the OAuth URL is printed to stdout — the user must visit it, authorize, and paste back the redirect URL.
5. Token is cached as `token.pickle` — subsequent runs don't need browser.

## First Upload Always Opens Browser

The `InstalledAppFlow.run_local_server()` starts a local HTTP server on **port 8080** and opens the Google consent page. In a background process, the browser won't open and the process will hang waiting for the redirect.

### ⚠️ Port 8080 Conflict with Docker Desktop

Docker Desktop binds port 8080 on Windows (via `com.docker.backend.exe`). The OAuth redirect will crash with:
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Fix**: Use a different port for the OAuth redirect:
```python
creds = flow.run_local_server(port=8081, open_browser=True)
```
The Google Cloud OAuth client is configured for the `http://localhost` redirect, so any port works — Google sends the auth code to `http://localhost:<port>/?code=...`.

**Check which port is free** (from bash):
```bash
# Test if 8081 is free
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081 2>/dev/null
# If connection refused (code 000 or empty), the port is free
```

Common occupied ports on this machine: 8080 (Docker), 8082 (legacy TTS), 8004 (current TTS), 8188 (ComfyUI).

**Recovery from stuck background OAuth**: Kill the stuck process, then run with port override:
```bash
cd ${MY_REPOS}/yt-animations
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', ['https://www.googleapis.com/auth/youtube.force-ssl'])
creds = flow.run_local_server(port=8081, open_browser=True)
import pickle
with open('token.pickle', 'wb') as f: pickle.dump(creds, f)
print('OAuth complete! Token saved.')
"
```

After the first successful auth (`token.pickle` saved), background processes can upload without interaction.

## Iterative Review Cycle (User's Preferred Workflow)

1. Upload video as **unlisted** for private review
   - Title format: `"Video Name (DRAFT)"`
2. User reviews on phone via `https://youtu.be/<video_id>`
3. If no good:
   - Tell agent to delete → agent runs `scripts/youtube_manager.py delete <video_id>`
   - Agent rebuilds with fixes → re-uploads
   - Repeat until user is satisfied
4. Never publish publicly on the first iteration

## Commands

```bash
# Upload for review
python scripts/youtube_manager.py upload outputs/slug/final/slug.final.mp4 \
  --title "Sycamore: The Hypothetical Heist (DRAFT)" \
  --description "Rough cut for mobile review." \
  --privacy unlisted

# Delete after review
python scripts/youtube_manager.py delete <video_id>

# List recent uploads
python scripts/youtube_manager.py list
```

## Via Pipeline

```bash
python create_video_v3.py \
  --topic "Title" --tts chatterbox \
  --upload --privacy unlisted \
  --yt-title "Title (DRAFT)" \
  --script-json outputs/script.json
```
