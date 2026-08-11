# Platform Automation Research Notes

## Fiverr Anti-Bot Protection

- **PerimeterX (Human Security)**: Fiverr uses `PXK3bezZfO` PerimeterX captcha
- **Detection level**: High — headless browsers trigger "It needs a human touch" challenge page immediately
- **Challenge types**: PerimeterX captcha (click-based), Cloudflare JS challenges
- **API**: Fiverr has NO public REST/GraphQL API for third-party developers
- **Key URLs**: 
  - `https://www.fiverr.com/login` — Login form
  - `https://www.fiverr.com/search/gigs?query=<term>` — Gig search
  - `https://www.fiverr.com/messages` — Inbox
  - `https://www.fiverr.com/dashboard/orders` — Orders page
- **First-time login**: Must use non-headless browser. 2FA/TOTP supported.
- **Session lifetime**: Cookies persist ~24-30 days with active use
- **Important**: PerimeterX uses fingerprinting. Multiple headless attempts from the same IP will blacklist it temporarily. Use session persistence to avoid repeated logins.

## Upwork Anti-Bot Protection

- **Cloudflare**: Upwork developer portal is behind Cloudflare Managed Challenge
- **Detection level**: Medium. Less aggressive than Fiverr but still protects login flow
- **API**: Upwork HAS a public GraphQL API (developer.upwork.com) but it's behind Cloudflare
  - REST API: `https://developers.upwork.com/` (requires API key access through Upwork's partnership program)
  - GraphQL API: Limited access, mostly for registered partners
- **Key URLs**:
  - `https://www.upwork.com/ab/account-security/login` — Login
  - `https://www.upwork.com/search/jobs/?q=<term>` — Job search
  - `https://www.upwork.com/ab/messages` — Messages
  - `https://www.upwork.com/ab/freelancer/contracts` — Contracts
- **First-time login**: May trigger security question (configure secret_answer)
- **Session lifetime**: Cookies persist ~7-14 days

## Recommended Libraries

| Library | Purpose |
|---------|---------|
| `undetected-playwright>=0.3.0` | Stealth browser automation (bypasses Cloudflare/PerimeterX with session cookies) |
| `playwright>=1.40` | Backend browser control (required by undetected-playwright) |
| `cloudscraper>=1.2.71` | Simple Cloudflare bypass for GET/POST (no login/interaction) |
| `beautifulsoup4` | HTML parsing for scraped content |
| `fake-useragent` | Random user agent generation |
| `pyotp` | TOTP 2FA code generation (Fiverr) |

## Session Cookie File Format

```json
// ~/.freelance-automation/cookies/fiverr_default.json
[
  {
    "name": "fiverr_session",
    "value": "abc123...",
    "domain": ".fiverr.com",
    "path": "/",
    "expires": 1745712345.0,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  }
]
```

## Price Parsing Patterns

Common price formats across freelance platforms:
- `$50` — simple
- `$1,500` — with comma
- `Starting at $25` — prefix text
- `$15 - $25/hr` — range
- `Budget: $500` — labeled

Use regex: `re.search(r'\$?([\d,]+(?:\.\d{1,2})?)', text.replace(",",""))`

## Number Normalization

Platforms use shorthand for large numbers:
- `1.5k` = 1500
- `2.3K` = 2300
- `500+` = 500
- `(123)` = 123

Handle with: `text.upper().replace(",",""), if "K" in text: int(float(text.replace("K","")) * 1000)`

## Account Creation Patterns

- **Email generation**: Generate as `platform.username.timestamp@gmail.com` — user needs access to verify
- **Password generation**: `secrets.choice(chars)` for 16-char passwords with mixed case + digits + special chars
- **CAPTCHA handling**: Build a 120s wait loop polling login state every 1s, print progress every 20s. User solves CAPTCHA in visible browser.
- **Form filling**: Multiple selector fallbacks per field (name, type, placeholder)
- **Post-creation**: Navigate to profile settings to add skills, bio, hourly rate, photo

## Smart Matching Engine — 53 Capabilities (8 domains)

**AI/ML**: AI automation, machine learning, LLM, GPT, chatbot, RAG, AI agents, prompt engineering, fine tuning, AI integration
**Programming**: Python, automation scripts, web scraping, API integration, backend dev, data pipelines, ETL, bot dev
**Cybersecurity**: pen testing, security audit, vulnerability assessment, ethical hacking
**Data**: data analysis, visualization, science, mining, web research, competitive analysis
**Business automation**: workflow automation, CRM automation, email automation, lead gen
**Our niches**: real estate tech, land analysis, property data, OSINT, threat intelligence

Scoring: skill match=+15, keyword bonus=+10-25, title match=+10 extra, easy-win keyword=+10 each. Floor=30.

## Easy-Win Keywords (2+ = flag)

"python script", "web scraping", "data extraction", "automation", "AI integration", "API integration", "chatbot", "data processing", "data cleaning", "web research", "bot development", "report generation", "csv", "excel automation", "file processing", "json", "database", "template", "configuration", "setup"

## AI Proposal Generation

Tailor on what matched: skills → "I specialize in X,Y,Z"; easy win → "I can complete efficiently"; budget → "within $X". Structure: greeting, skill alignment, specific offer, timeline, CTA, signature.

## Fiverr Gig Pricing Tiers

| Category | Basic | Standard | Premium |
|----------|-------|----------|---------|
| AI Automation | $50 (3d) | $150 (5d) | $500 (7d) |
| Python Dev | $30 (2d) | $100 (4d) | $300 (7d) |
| Data Analysis | $40 (3d) | $120 (5d) | $350 (7d) |
| Web Scraping | $35 (2d) | $100 (4d) | $250 (7d) |
| Chatbot Dev | $60 (3d) | $200 (5d) | $600 (7d) |

## Cron Monitoring Pattern

Reports: `reports/scan_{timestamp}.json`. Dedup key: `{platform}:{title}:{url}`. Aggregates: top skills in demand, by-platform counts. Report shape: total_new, easy_wins, high_value, top_matches (with scores/URLs/reasons), easy_win_opportunities.

## Concrete Project: Fiverr/Upwork Automation Suite

Built at `~/freelance-automation/` (3,369 lines, 15 files). Full implementation of this skill's architecture:

- **browser.py** — StealthBrowser with session persistence, human-like typing/scroll
- **config.py** — Credential management, cookie/session paths
- **profile_manager.py** — Multi-account profiles with metadata (skills, hourly rate, timestamps)
- **platforms/fiverr/__init__.py** — Fiverr: research_gigs, analyze_niche, get_messages, send_message, get_orders, login (2FA support)
- **platforms/upwork/__init__.py** — Upwork: search_jobs, analyze_job_market, get_messages, send_message, submit_proposal, get_contracts, login (security question support)
- **job_matcher.py** — JobMatcher (score_job, filter_and_rank, generate_proposal, generate_gig_description) + 53 capabilities across 8 domains
- **auto_applicant.py** — AutoApplicant (scan_and_apply, submit_proposals) + GigPoster (post_fiverr_gig)
- **account_creator.py** — AccountCreator (create_fiverr_account, create_upwork_account)
- **job_monitor.py** — JobMonitor (scan_run, setup_cron, get_summary)
- **main.py** — 16 CLI commands (setup, login, create-account, research, analyze, scan, apply, post-gig, monitor, monitor-setup, full, batch, messages, send, orders, proposal)
- **launch.py** — One-click pipeline launcher (python launch.py --all)

### Key commands
```bash
python main.py create-account --platform fiverr   # guided account creation
python main.py login --platform fiverr             # establish session
python main.py scan --terms "AI,Python,automation"  # search + score + generate proposals
python main.py apply                                # submit proposals
python main.py post-gig --query "AI Automation"     # create Fiverr gig
python main.py monitor                              # one scan
python main.py monitor-setup --pages 4              # cron every 4h
```

## Pitfalls from This Session

- **argparse choices vs commands dict**: Keep in sync. A mismatch silently ignores the command.
- **Dataclass required fields**: All non-default fields must be provided on construction.
- **PerimeterX "human touch" is normal**: Even with stealth, Fiverr shows this. Session cookies from real login fix it, not more stealth.
- **f-strings in bash heredocs**: Write multiline Python with f-strings inside bash causes parse errors. Use separate .py files.
- **Capability matrix needs maintenance**: Keep as standalone constants module for easy updates as niches emerge.
