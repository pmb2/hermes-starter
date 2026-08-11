---
name: social-media-automation
description: "Full social media automation stack: Postiz (self-hosted multi-platform scheduling with MCP/CLI), instagrapi (publishing API), InstaPy (engagement bot), Remotion (programmatic video)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [social-media, instagram, automation, video-generation, social-media-scheduling, postiz, instagrapi, instapy, remotion]
    triggers: [social-media, instagram, automation, content-publishing, engagement-growth, social-media-scheduling, self-hosted-social-media, postiz, instagrapi, instapy, remotion]
    related_skills: [writing-plans, subagent-driven-development, native-mcp]
---

# Social Media Automation — Tool Integration Guide

## Overview

Four tiers of open-source tools form a complete social media automation stack:

| Tool | Role | Language | Stars | Key Strength |
|------|------|----------|-------|-------------|
| **Postiz** (`gitroomhq/postiz-app`) | Full platform | TypeScript/NestJS | 10K+ | Self-hosted Buffer alternative, 28+ platforms, scheduling, MCP server |
| **instagrapi** (`subzeroid/instagrapi`) | Publishing API | Python | 6.2K | Mobile/Web private API — photo/video/story/DM upload |
| **InstaPy** (`InstaPy/InstaPy`) | Engagement bot | Python | 17.9K | Selenium-based liking, commenting, following automation |
| **Postiz** (`gitroomhq/postiz-app`) | Full platform | TypeScript/NestJS | 10K+ | Self-hosted Buffer alternative, 28+ platforms, scheduling, MCP server |

### Brand-Building Mode

When the user frames the work as "build my brand" or "you are my social media manager," treat this skill as the tooling layer under `social-brand-manager`. Start with the `social-brand-manager` playbook (asset audit, brand architecture, content pillars), then return here to deploy Postiz and automate publishing.

**Division of responsibility:**
- **Postiz** = multi-platform scheduling + analytics + team management (the strategic layer)
- **instagrapi** = low-level Instagram publishing (upload photos, videos, reels, stories, send DMs, get analytics)
- **InstaPy** = engagement (like, comment, follow by hashtag/location/user — organic growth)
- **Remotion** = content creation (generate property reels, market updates, branded videos programmatically)

## When to Use

- Managing multiple social media accounts across 28+ platforms with scheduling + analytics → **Postiz**
- Building an AI agent that needs to post on social media → **Postiz** (has MCP server, CLI, and REST API)
- Adding just Instagram capabilities to a project → **instagrapi** (lighter weight)
- Automating Instagram engagement for organic growth → **InstaPy**

**Don't use for:**
- Simple scheduled posting (use Instagram Creator Studio / Meta Business Suite directly)
- Large-scale bot farms (instagrapi warns about reliability)
- Circumventing Instagram's terms of service for spam

## Brand Vetting Before Account Creation

Before buying domains or claiming social handles for a new brand, run a systematic availability sweep. A name that is taken on core platforms creates friction, SEO competition, and trademark risk.

### Checklist (in order)

1. **Exact-phrase Google search** `"Brand Name"` — look for active companies, products, or communities
2. **Domains** — `.com`, `.co`, `.io`, `.ai`, `.app` via DNS resolution or registrar availability
3. **GitHub** — `/orgname`, `/orgname-hq`, and exact user handles
4. **X/Twitter** — profile URL returns 200 with a real profile title
5. **Instagram** — profile title contains the handle or "Instagram photos"
6. **YouTube** — `@handle` channel exists
7. **LinkedIn company** — `/company/handle`
8. **Reddit** — `/r/handle`
9. **Bluesky** — `handle.bsky.social`
10. **Threads** — `@handle`
11. **Pinterest** — `/handle/`
12. **Substack** — `handle.substack.com`
13. **Medium** — `@handle`
14. **beehiiv** — `handle.beehiiv.com`
15. **App stores** — Play Store + App Store search for the phrase
16. **Trademark** — USPTO NOTES / Trademarkia search

### Decision Rule

Require **at least** the `.com` or `.io` + primary social handle (`@handle` on X and Instagram) to be available before committing to a name. If a name is taken on three or more core platforms, reject it and generate alternatives.

### Reusable Probe Script

See `references/brand-vetting-probe.py` for a Python script that checks domains, GitHub, X, Instagram, YouTube, LinkedIn, Reddit, Bluesky, Threads, Pinterest, Substack, Medium, and Google exact-phrase results in one run.

## Autonomous AI Content Account

A common brand-building objective is a fully autonomous account that publishes AI news, facts, tips, and tricks aligned with specific ICPs. Treat this as a pipeline:

1. **Sources** — RSS feeds, Reddit, arXiv, AI newsletters, GitHub trending, HuggingFace papers
2. **Curator** — LLM filters for relevance to each ICP and novelty
3. **Rewriter** — convert source into native posts per platform (X thread, LinkedIn text, Instagram carousel, TikTok script)
4. **Scheduler** — Postiz CLI or MCP `schedulePostTool`
5. **Video tier** — later add Remotion / fal.ai / Higgsfield for video posts
6. **Engagement tier** — optional InstaPy for organic growth (strict daily limits)

### ICP-Aligned Content Pillars

For a builder with three lanes (websites for local services, website landlord/lead-gen, high-ticket AI systems), split posts across pillars:

| Day | Pillar | Example Hook |
|-----|--------|--------------|
| Mon | AI news for operators | "OpenAI just shipped X. Here's what it changes for service businesses..." |
| Tue | Local business AI tips | "A plumber in Albany used this one AI workflow to cut admin time 40%..." |
| Wed | Website/lead-gen strategy | "The local SEO gap most contractors ignore..." |
| Thu | AI agent builds | "I built an AI phone agent for $12/month. Here's the stack..." |
| Fri | Tooling/facts | "5 MCP servers that actually save hours..." |
| Sat | Case study/personal build | "This week I deployed 12 sites in one night..." |
| Sun | Curation/roundup | "Best AI releases this week..." |

### Video-First Upgrade Path

When ready, generate video from the same source post:
- **Remotion** for data-driven / text-heavy explainers
- **fal.ai** for image/video generation
- **Higgsfield** for character/avatar-driven clips

Render once, publish to YouTube Shorts, TikTok, Instagram Reels, and X via Postiz with platform-specific captions.

## Architecture Pattern

### Recommended Architecture: BullMQ + Python Bridge

```
┌──────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Node.js App  │────▶│   BullMQ    │◀────│  Remotion Worker  │
│  (Next.js)    │     │  (Redis)    │     │  (Node.js)        │
└──────────────┘     └──────┬──────┘     └──────────────────┘
                            │
               ┌────────────┼────────────┐
               │            │            │
      ┌────────┴───┐ ┌─────┴─────┐ ┌───┴────────┐
      │ instagrapi  │ │ InstaPy   │ │ Other      │
      │ Bridge      │ │ Worker    │ │ Publishers │
      │ (FastAPI)   │ │ (Python)  │ │ (LinkedIn/ │
      │ port:8000   │ │           │ │ FB/Twitter)│
      └────────────┘ └───────────┘ └────────────┘
```

**Key design decisions:**
- Python microservice (FastAPI) bridges Node.js <-> instagrapi/InstaPy
- Session persistence in Redis (TTL: 7 days) + PostgreSQL fallback
- BullMQ queues for async publishing, engagement, and video rendering
- Encrypted credential storage for Instagram accounts
- Challenge handling hooks with admin escalation

## instagrapi — Quick Start

### Installation

```bash
pip install instagrapi
pip install "instagrapi[curl]"  # optional TLS impersonation
```

### Basic Login & Upload

```python
from instagrapi import Client

cl = Client()
cl.login("username", "password")

# Upload photo
media = cl.photo_upload("path/to/photo.jpg", "Amazing caption! #realestate")
print(f"Uploaded: {media.pk}")

# Upload video/Reel
cl.clip_upload("path/to/video.mp4", "Check out this tour! #home")

# Upload story
cl.photo_upload_to_story("path/to/photo.jpg", "Swipe up! 👆")
```

### Session Persistence

```python
# Save session after login
cl.dump_settings("session.json")

# Reload later
cl = Client()
cl.load_settings("session.json")
cl.login("username", "password")  # lightweight re-auth
```

### Story with Stickers

```python
from instagrapi.types import StoryMention, StoryLink, StoryHashtag

user = cl.user_info_by_username("subzeroid")
hashtag = cl.hashtag_info("realestate")

cl.photo_upload_to_story(
    "photo.jpg",
    "Check this out!",
    mentions=[StoryMention(user=user, x=0.5, y=0.7, width=0.4, height=0.1)],
    links=[StoryLink(webUri='https://example.com/listing')],
    hashtags=[StoryHashtag(hashtag=hashtag, x=0.2, y=0.3, width=0.3, height=0.2)]
)
```

### Session with Redis

```python
import json, redis

r = redis.from_url("redis://localhost:6379")

# After login
session_key = f"ig_session:{username}"
r.set(session_key, json.dumps(cl.get_settings()), ex=86400*7)

# On reload
cl = Client()
cl.set_settings(json.loads(r.get(session_key)))
```

### Analytics

```python
insights = cl.account_insights()
print(insights)

# User info
user_id = cl.user_id_from_username("target_user")
user_info = cl.user_info_by_username("target_user")
medias = cl.user_medias(user_id, 20)
```

### Error Handling

```python
from instagrapi.exceptions import LoginRequired, ClientNotFoundError, ChallengeRequired

try:
    cl.photo_upload("photo.jpg", "caption")
except LoginRequired:
    # Re-login
    cl.login(username, password)
except ChallengeRequired:
    # Handle challenge (email/SMS code)
    pass
```

## InstaPy — Engagement Automation

### Installation

```bash
pip install instapy
```

### Basic Engagement Session

```python
from instapy import InstaPy

session = InstaPy(
    username="your_username",
    password="your_password",
    headless_browser=True
)

session.login()

# Configure engagement
session.set_do_like(enabled=True, percentage=70)
session.set_do_comment(enabled=True, percentage=25)
session.set_comments(['Nice!', 'Great post!', 'Love this!'])
session.set_do_follow(enabled=True, percentage=10)

# Set delays (anti-ban)
session.set_action_delays(enabled=True, like=10, comment=30, follow=20)

# Target by hashtag
session.like_by_tags(['realestate', 'dreamhome'], amount=30)

# Target by location
session.like_by_location('New York', amount=20)

session.end()
```

### Safety Configuration

```python
# Daily limits (embedded in worker config)
DAILY_LIMITS = {
    "likes": 150,
    "comments": 30,
    "follows": 60,
    "unfollows": 30,
}

# Session caps
MAX_SESSION_MINUTES = 45
MAX_POSTS_PER_HASHTAG = 5
```

### AI-Generated Comments

```python
# Pull comments from SocialGenius LLM instead of static list
comments = [
    "Beautiful property! What's the square footage? 🏡",
    "Love the kitchen renovation in this one!",
    "Dream home material right here 💯",
]
session.set_comments(comments)
```

### Docker Deployment

```yaml
services:
  instapy-worker:
    build: ./instapy-worker
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    shm_size: 2gb   # Required for Chromium
```

## Remotion — Programmatic Video

### Installation

```bash
npx create-video@latest
npm i remotion @remotion/bundler @remotion/renderer
```

### Basic Component

```tsx
import { AbsoluteFill, Sequence, useCurrentFrame, interpolate } from 'remotion';

export const MyVideo: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#1a1a2e', opacity }}>
      <h1 style={{ color: 'white', fontSize: 60 }}>{title}</h1>
    </AbsoluteFill>
  );
};
```

### Rendering from Node.js

```typescript
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';

const bundleLocation = await bundle({ entryPoint: '/path/to/root.ts' });
const composition = await selectComposition({
  serveUrl: bundleLocation,
  id: 'my-composition',
  inputProps: { title: 'Hello' },
});

await renderMedia({
  composition,
  serveUrl: bundleLocation,
  codec: 'h264',
  outputLocation: '/tmp/output.mp4',
  inputProps: { title: 'Hello' },
});
```

### BullMQ Render Worker Pattern

```typescript
const worker = new Worker('video-render', async (job) => {
  const { template, props } = job.data;

  // 1. Bundle
  const bundleLocation = await bundle({ entryPoint });

  // 2. Select composition
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: template,
    inputProps: props,
  });

  // 3. Render
  const outputPath = `/renders/${job.id}.mp4`;
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: props,
  });

  return { outputPath };
}, { connection: redisConnection });
```

## Postiz — Self-Hosted Social Media Platform

**Postiz** (`gitroomhq/postiz-app`) is a full self-hosted alternative to Buffer / Hypefury / Later. Runs on Docker Compose with Next.js (frontend), NestJS (API), Temporal (workflow engine), PostgreSQL, and Redis.

| Aspect | Detail |
|--------|--------|
| Platforms | 28+ — X/Twitter, LinkedIn, Instagram, TikTok, YouTube, Facebook, Reddit, Discord, Slack, Bluesky, Mastodon, Threads, Pinterest, Telegram, Medium, Dev.to, WordPress, and more |
| Agent Integration | MCP server (HTTP streaming, Bearer token), CLI (npm install -g postiz), REST API |
| License | AGPL-3.0 |
| GitHub | https://github.com/gitroomhq/postiz-app |

### Mixpost — Lightweight Self-Hosted Alternative

**Mixpost** (`inovector/mixpost`) is a lighter-weight, Laravel-based self-hosted scheduler. It is a good parallel or alternative to Postiz when you want a simpler PHP/MySQL stack instead of Temporal + NestJS.

| Aspect | Detail |
|--------|--------|
| Platforms | X/Twitter, LinkedIn, Facebook, Instagram, TikTok, YouTube, Pinterest, Bluesky, Mastodon, Threads |
| Stack | Laravel, PHP, MySQL/PostgreSQL, Redis |
| GitHub | https://github.com/inovector/mixpost |

**When to choose Mixpost over Postiz:**
- Smaller resource footprint (no Temporal workflow engine)
- You prefer PHP/Laravel ops
- Scheduling + basic analytics are enough; you don't need the MCP agent layer

**Recommended architecture:** run **both** Postiz and Mixpost side-by-side on different ports. Use Postiz as the primary agent-facing scheduler (MCP + CLI), and Mixpost as a backup/secondary queue for redundancy or for team members who prefer its UI.

```yaml
# Minimal Mixpost Compose snippet (see references/mixpost-docker-compose.yaml for full file)
services:
  mixpost:
    image: inovector/mixpost:latest
    ports:
      - "4008:80"
    environment:
      APP_URL: "http://localhost:4008"
      DB_DATABASE: mixpost
      DB_USERNAME: mixpost
      DB_PASSWORD: changeme
    depends_on:
      - mixpost-mysql
      - mixpost-redis
```

### When to Use Postiz vs Mixpost vs Lower-Level Tools

| Need | Use |
|------|-----|
| Multi-platform scheduling, MCP/agent integration | Postiz |
| Lightweight self-hosted scheduler (no Temporal) | Mixpost |
| Just Instagram publishing | instagrapi (lighter weight) |
| Instagram engagement farming | InstaPy (liking/commenting/following) |
| Scheduled AI-powered posting via an agent | Postiz MCP server (agent calls schedulePostTool) |
| Programmatic video then post | Remotion + Postiz API (render then schedule) |

### Quick Setup (Docker Compose)

```bash
git clone https://github.com/gitroomhq/postiz-app.git
cd postiz-app
# Configure .env with JWT_SECRET, etc.
docker compose up -d
```

Key settings in `docker-compose.yaml`:
- Frontend: port 4007 (maps to container port 5000)
- API: `http://localhost:4007/api`
- PostgreSQL, Redis, Temporal auto-configured
- No Cloudflare R2 needed for local dev — use `STORAGE_PROVIDER=local`

After startup, register the first account at http://localhost:4007 (auto-activates when RESEND_API_KEY isn't set).

### Connecting Social Accounts

Each platform requires OAuth credentials configured as env vars in docker-compose.yaml. Common ones:

| Platform | Required Env Vars | OAuth Redirect URI |
|----------|------------------|-------------------|
| X/Twitter | `X_API_KEY`, `X_API_SECRET` | `{FRONTEND_URL}/integrations/social/x` |
| LinkedIn | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | (in-app OAuth) |
| YouTube / Google | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` | `{FRONTEND_URL}/integrations/social/youtube` |
| Google My Business | `GOOGLE_GMB_CLIENT_ID`, `GOOGLE_GMB_CLIENT_SECRET` | `{FRONTEND_URL}/integrations/social/gmb` |
| Instagram | `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` (via Facebook Business), or Instagram Standalone | (in-app OAuth) |
| TikTok | `TIKTOK_CLIENT_ID`, `TIKTOK_CLIENT_SECRET` | `{FRONTEND_URL}/integrations/social/tiktok` |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | `{FRONTEND_URL}/integrations/social/reddit` |
| Bluesky | No OAuth needed — connect via username/password in UI | — |
| Mastodon | No OAuth needed — connect via instance URL + credentials | — |

After adding env vars, restart the stack: `docker compose up -d`

### Postiz CLI — Agent Use

```bash
npm install -g postiz
export POSTIZ_API_KEY="your-api-key"     # From Settings > Developers
export POSTIZ_API_URL="http://localhost:4007/api"  # Self-hosted only

# List connected integrations
postiz integrations:list

# Schedule a post
postiz posts:create -c "Post content" -s "2024-12-31T12:00:00Z" -i "integration-id"

# Post with comments
postiz posts:create -c "Main post" -c "First comment" -s "2024-12-31T12:00:00Z" -i "integration-id"

# Post with media
postiz posts:create -c "Content" -m "image.jpg" -s "2024-12-31T12:00:00Z" -i "integration-id"
```

### MCP Server (for AI Agent Integration)

Postiz exposes a streamable HTTP MCP endpoint at `/api/mcp` with 9 tools:

| Tool | Purpose |
|------|---------|
| `integrationList` | List connected social accounts |
| `groupList` | List groups/customers |
| `integrationSchema` | Get platform-specific posting rules |
| `triggerTool` | Execute platform helpers (list Discord channels, Reddit flairs, etc.) |
| `schedulePostTool` | Schedule, draft, or publish posts |
| `generateImageTool` | Generate AI images for posts |
| `generateVideoOptions` | List video generation options |
| `videoFunctionTool` | Get video generator settings |
| `generateVideoTool` | Generate videos for posts |

**Hermes config example (HTTP transport):**

```yaml
mcp_servers:
  postiz-mcp:
    url: "http://localhost:4007/api/mcp"
    headers:
      Authorization: *** <your-api-key>"
    timeout: 120
    connect_timeout: 30
```

### Google OAuth Setup (YouTube / GMB)

Postiz uses Google OAuth via the `google-auth-library`. Both YouTube and Google My Business share the same OAuth client config — GMB falls back to `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET` if its own vars aren't set.

**Redirect URIs needed in the Google Cloud Console OAuth client:**
- `{FRONTEND_URL}/integrations/social/youtube`
- `{FRONTEND_URL}/integrations/social/gmb`

**Steps:**
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a **Web application** OAuth client
3. Add `https://sg.your-domain.example` (or your domain) under Authorized JavaScript origins
4. Add the redirect URIs above
5. Copy Client ID and Client Secret into `docker-compose.yaml` as `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `GOOGLE_GMB_CLIENT_ID`, `GOOGLE_GMB_CLIENT_SECRET`
6. Restart the stack: `docker compose up -d`

> The same OAuth client can serve both YouTube and GMB — just add both redirect URIs.

### Getting an API Key

1. Navigate to Settings > Developers > Public API
2. Reveal and copy the API key
3. Use with CLI (`export POSTIZ_API_KEY=*** MCP (Bearer token), or REST API

### Configuring a Public Domain (Production)

To expose Postiz on a real domain instead of localhost:

1. **Update docker-compose.yaml env vars** to match the target domain:
   ```yaml
   environment:
     MAIN_URL: 'https://sg.your-domain.example'
     FRONTEND_URL: 'https://sg.your-domain.example'
     NEXT_PUBLIC_BACKEND_URL: 'https://sg.your-domain.example/api'
     BACKEND_INTERNAL_URL: 'http://localhost:3000'  # internal stays local
   ```

2. **DNS**: Point the domain's A/AAAA record to the server's public IP.

3. **Reverse proxy** (recommended): Put Nginx/Caddy/Traefik in front. For Caddy, a simple `Caddyfile`:
   ```
   sg.your-domain.example {
       reverse_proxy localhost:4007
   }
   ```

4. **Update social platform OAuth apps** with the new redirect URIs (e.g. `https://sg.your-domain.example/integrations/social/x`).

5. Not all platforms work behind a proxy — test each one. Some (like TikTok) require exact URI match between the platform app config and the running instance.

6. Restart the stack after changes: `docker compose up -d`

> **Docker Desktop on Windows — port 80/443 conflict:** Docker's internal networking (com.docker.backend.exe + wslrelay.exe) typically reserves ports 80 and 443 on 0.0.0.0. If a reverse proxy container fails with "port is already allocated", bind to the machine's public IP instead: `"74.76.35.96:80:80"`. Or use alternate ports (8080/8443) and include the port in the FRONTEND_URL.

### REST API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/public/v1/posts` | POST | Create a post |
| `/public/v1/posts` | GET | List posts |
| `/public/v1/posts/:id` | DELETE | Delete a post |
| `/public/v1/integrations` | GET | List integrations |
| `/public/v1/groups` | GET | List groups |
| `/public/v1/upload` | POST | Upload media |
| `/public/v1/analytics/:integration` | GET | Platform analytics |

### Pitfalls

1. **MCP transport mismatch.** Postiz uses HTTP streaming (not stdio). In Hermes config, use `url:` + `headers:` format, NOT `command:` + `args:`.
2. **Self-hosted API URL.** The CLI defaults to `https://api.postiz.com`. Always set `POSTIZ_API_URL` for self-hosted instances.
3. **OAuth redirect URIs.** For social platform OAuth, the redirect URI must point to your self-hosted Postiz (e.g., `http://localhost:4007/integrations/social/x`). Edit the OAuth app settings on each platform.
4. **Temporal overhead.** Postiz includes a full Temporal workflow engine stack (5+ containers). Ensure sufficient Docker resources (4GB+ RAM recommended).
5. **Elasticsearch on Windows.** Elasticsearch may fail on some Windows Docker setups due to vm.mmap_count limit. Test the docker compose stack on your machine before depending on it.
6. **Agent built-in vs MCP.** Postiz has a built-in chat agent at `/agents` that can schedule posts and generate media. This is separate from the MCP server — both can be used simultaneously.

### Verification Checklist

- [ ] Docker containers all healthy (`docker compose ps`)
- [ ] Can register account and log into web UI (http://localhost:4007)
- [ ] API key visible in Settings > Developers
- [ ] `postiz auth:status` returns valid credentials
- [ ] `postiz integrations:list` returns expected integrations (empty is OK before connecting accounts)
- [ ] MCP endpoint responds: `curl -H "Accept: application/json, text/event-stream" http://localhost:4007/api/mcp`
- [ ] Social platforms connected (OAuth completed in web UI)

## Integration Tips

### Python Bridge (FastAPI) Skeleton

```python
from fastapi import FastAPI, HTTPException
from instagrapi import Client
import redis, json

app = FastAPI(title="Instagram Bridge")
r = redis.from_url("redis://localhost:6379")

def get_client(session_key: str) -> Client:
    cl = Client()
    settings = r.get(f"ig_session:{session_key}")
    if not settings:
        raise HTTPException(401, "Session not found")
    cl.set_settings(json.loads(settings))
    return cl

@app.post("/upload/photo")
def upload_photo(session_key: str, photo_path: str, caption: str):
    cl = get_client(session_key)
    result = cl.photo_upload(photo_path, caption)
    return {"media_id": result.pk}
```

### BullMQ Job Types

```typescript
// Publishing queue
await publishQueue.add('instagram-publish', {
  type: 'photo',       // photo | video | reel | story | dm
  sessionKey: '...',
  mediaPath: '/tmp/photo.jpg',
  caption: 'Amazing! #home',
});

// Engagement queue
await engagementQueue.add('instagram-engage', {
  hashtags: ['realestate'],
  likes: 30,
  comments: 10,
  follows: 5,
});

// Video render queue
await renderQueue.add('video-render', {
  template: 'property-reel',
  props: { photos: [...], address: '...', price: '...' },
});
```

### Security Checklist

- [ ] Encrypt Instagram passwords at rest (AES-256-GCM)
- [ ] Never log credentials
- [ ] Daily action limits per account (like/follow/comment caps)
- [ ] Randomized delays between actions (not fixed intervals)
- [ ] Session TTL with proactive refresh (don't wait for expiration)
- [ ] Challenge handler: auto-fill from email inbox + admin escalation
- [ ] Proxy rotation for multiple accounts
- [ ] Separate Docker containers for Python bridge services
- [ ] Health check endpoints on all bridge services

## Common Pitfalls

1. **Not persisting sessions.** Login every time = rate limit triggers fast. Always `dump_settings()` and reuse.
2. **Aggressive engagement.** More than 150 likes/day triggers Instagram's action blocks. Start conservatively.
3. **No challenge handling.** instagrapi raises `ChallengeRequired` — needs resolver hooks. Check the `handle_exception` guide.
4. **Headless browser memory.** InstaPy needs Chromium in Docker — allocate `shm_size: 2gb`.
5. **Remotion license.** Remotion requires a company license for commercial use. Verify before deploying.
6. **Python <-> Node bridge latency.** Keep bridge calls async via BullMQ. Don't block HTTP request handlers on uploads.
7. **Selenium selector staleness.** InstaPy's Selenium selectors can break when Instagram updates UI. Pin a known-working version.

## Verification Checklist

- [ ] instagrapi can login, upload photo, upload video, send DM
- [ ] Session persists across container restarts (Redis + dump)
- [ ] InstaPy can run headless, target hashtags, set delays, set action limits
- [ ] Remotion can render a 15-second video from React component
- [ ] BullMQ workers pick up jobs from the queue and call the bridge
- [ ] Challenge handler resolves email/SMS verification
- [ ] Daily action limits are enforced (not exceeded)
- [ ] Credentials are encrypted at rest and in transit
- [ ] Docker Compose starts all services with proper dependencies

## References

- [Postiz GitHub](https://github.com/gitroomhq/postiz-app)
- [Postiz Docs](https://docs.postiz.com/)
- [Postiz CLI Docs](https://docs.postiz.com/cli/introduction)
- [Postiz MCP Docs](https://docs.postiz.com/mcp/introduction)
- [Postiz Public API](https://docs.postiz.com/public-api)
- [Postiz Agent CLI (npm)](https://www.npmjs.com/package/postiz)
- [instagrapi Docs](https://subzeroid.github.io/instagrapi/)
- [instagrapi Error Handling](https://instagrapi.com/guides/errors/)
- [InstaPy Docs](https://github.com/InstaPy/InstaPy/blob/master/docs/home.md)
- [Remotion Docs](https://www.remotion.dev/docs/)
- [instagrapi Session Persistence Guide](https://instagrapi.com/guides/instagrapi-session-persistence/)
- [Framework Integrations (Django, FastAPI, Celery, Docker)](https://instagrapi.com/guides/integrations/)

## Support Files

- **`references/postiz-api-client-pattern.py`** — Ready-to-use Python HTTP client for the Postiz REST API. Covers list integrations, create posts, upload media, and sports-pick/challenge publication. Drop into any AI agent or cron script that needs to post to social media.
- **`references/brand-vetting-probe.py`** — Reusable script that checks domains, social handles, GitHub, Reddit, Bluesky, and exact-phrase Google search for a brand name. Run before committing to a name.
- **`references/mixpost-docker-compose.yaml`** — Minimal Docker Compose for self-hosted Mixpost, suitable for running alongside Postiz on a different port.
