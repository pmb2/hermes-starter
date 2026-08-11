# InnerTube API & Cookie-Based Auth for YouTube Transcripts

When `youtube-transcript-api` returns `IpBlocked` or `RequestBlocked` (after ~400 requests/IP), use the browser's authenticated session to bypass rate limits.

## Approach 1: Browser InnerTube API (Recommended)

YouTube's internal API endpoint works when called from within a logged-in browser session:

```javascript
// POST to InnerTube player API
const resp = await fetch('https://www.youtube.com/youtubei/v1/player?key=AIzaSy<your-yt-api-key>', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        context: {
            client: {clientName: 'WEB', clientVersion: '2.20240501.00.00', hl: 'en'}
        },
        videoId: videoId,
    }),
});
const data = await resp.json();
const tracks = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
```

The `captions.playerCaptionsTracklistRenderer.captionTracks` array contains available caption tracks. Each track has:
- `baseUrl` — URL to fetch the transcript XML
- `languageCode` — e.g. "en", "es"
- `name.simpleText` — display name

Fetching the transcript XML:
```javascript
const xmlResp = await fetch(track.baseUrl);
const xml = await xmlResp.text();
// Parse XML <text> elements
const regex = /<text[^>]*start="([\d.]+)"[^>]*dur="([\d.]+)"[^>]*>(.*?)<\/text>/g;
```

## Approach 2: Python with Browser Cookies

Extract cookies from Firefox profile and use with `youtube-transcript-api`:

```python
import requests as req
from youtube_transcript_api import YouTubeTranscriptApi

session = req.Session()
# Populate with cookies from Firefox (cookies.sqlite in profile dir)
api = YouTubeTranscriptApi(http_client=session)
transcript = api.fetch(video_id)
```

## API Key

The InnerTube API key (`AIzaSy<your-yt-api-key>`) is YouTube's internal web client key. It's embedded in the YouTube web app source — not a secret, but use responsibly.

## Important Notes

- The InnerTube API response may not include captions if the video genuinely has none
- Some videos return `playabilityStatus` but no `captions` — these truly lack transcripts
- The browser must be navigated to a YouTube page first to establish session cookies
- Rate limits on the InnerTube API are per-session, so browser auth resets them
