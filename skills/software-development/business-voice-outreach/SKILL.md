---
name: business-voice-outreach
description: >-
  Calibrate AI writing to match a specific human voice, then use that voice
  for C2C business development outreach. Covers voice profile building from
  writing samples, outreach strategy for small-mid companies, business-hours
  sending discipline, and Gmail SMTP integration for the BizDev pipeline.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [voice, outreach, c2c, email, bizdev, style, writing]
    triggers:
      - brand voice
      - voice calibration
      - writing style
      - outreach
      - c2c
      - email outreach
      - prospecting
      - bizdev
      - income
    related_skills: [humanizer, bizdev-agent]
---

# Business Voice Outreach

Calibrate AI-generated outreach to sound like a specific person, then use
that voice for C2C contract hunting. This skill bridges the humanizer (voice
calibration) and the BizDev agent (pipeline management).

## When to use this skill

Load this when the user asks to:
- "capture my voice" / "write like me" / "make it sound like I wrote it"
- set up C2C or business development outreach (tech staffing, MES, A&D, AI services)
- generate emails or messages for contract/sales opportunities
- "not sound like AI" / "not be robotic" in business communications
- review drafts for AI tells before sending
- research and target companies for contracts

**Do NOT load this for land wholesale builder outreach.** That is a different
domain with different audience dynamics, suspicions, and voice requirements.
Use `land-acquisition-operations` + `builder-relationship-playbook` instead.

## Voice Calibration Workflow

### 1. Gather writing samples

Best sources (in order of usefulness):
- **Sent emails** from the user's Gmail Sent folder via IMAP (himalaya or
  Python imaplib). The user must generate an App Password first:
  Google Account > Security > App Passwords.
- **Discord messages** the user has sent (pull from session history)
- **Drafts or documents** the user provides

For Gmail IMAP:
```python
import imaplib, email
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login("user@gmail.com", app_password.replace(" ", ""))
mail.select('"[Gmail]/Sent Mail"')
status, ids = mail.search(None, "ALL")
# Fetch recent 200, filter out auto-generated/system emails
```

### 2. Filter and analyze

Skip auto-generated: cron reports, bot digests, heartbeats, job alerts,
order confirmations, templated replies. Keep only human-written messages.

For each kept sample, note:
- Sentence length (short punchy? long flowing? mixed?)
- Paragraph structure (how many sentences? how do they transition?)
- Word choice (casual? formal? contractions? slang?)
- Openers ("Hey [Name]," vs "Dear" vs "Hello")
- Closers (signature style)
- Punctuation habits (dashes, parentheticals, semicolons)
- Any repeated phrases or verbal tics

### 3. Build a voice profile JSON

```json
{
  "openers": ["Hey [Name],", "Hello [Team],"],
  "closers": ["Cheers,", "the operator"],
  "voice_rules": {
    "paragraphs": "Short. 1-4 sentences. New topic = new paragraph.",
    "contractions": true,
    "tone": "Direct, casual-professional. Knows value, does not over-explain.",
    "tells_to_avoid": [
      "No em dashes or hyphenated compounds. Use commas or periods instead. 'Game-changer' becomes 'game changer' or 'huge advantage.'",
      "No 'I hope this finds you well' or 'I am writing to'",
      "No 'Please do not hesitate to' or 'In today's fast-paced'",
      "No rule-of-three lists",
      "No generic positive conclusions ('looks bright', 'exciting times')",
      "No hype words: game-changing, revolutionary, groundbreaking",
      "No collaborative artifacts: 'Of course!', 'Certainly!', 'Let me know if'",
      "No sycophantic/corny tone",
      "No semicolons in short business emails"
    ],
    "voice_markers": [
      "Gets straight to the point",
      "Confident without being aggressive",
      "Short subject lines. Not generic.",
      "Uses contractions naturally (I'm, I'd, I've, don't)"
    ]
  }
}
```

## Outreach Rules (C2C specific)

### Timing
- **Business hours only** for sending email: 9am-5pm ET, Monday-Friday.
- **Off hours** (after 5pm ET, weekends): research, recon, prep, tooling.
  Never send during off hours.
- Best send window: B2B outreach Tue-Thu 9-11am ET.

### Targeting (C2C-specific)

**Direct C2C only** — the company invoices the client directly.

- Subcontracting through layers/SIs IS acceptable IF they contract on
  **capability** (Solumina/MES expertise, delivery track record), not
  individual background vetting (security clearance, ITAR certification
  as a person, background investigation).
- Avoid primes (Lockheed, RTX, Boeing, Northrop, L3Harris, GD) directly
  — too much vendor scrutiny for a C2C individual. Only engage through
  a capability-focused SI/partner layer that values delivery.
- No roles requiring personal background checks, individual ITAR
  certification, or personal security clearance.

**Creative approaches (not spray-and-pray):**

1. **Define ICPs** — who specifically has the MES/Solumina problem you solve
2. **Define specific offerings** — exact service packages with deliverables
3. **Find decision makers** — research by name, title, company
4. **Multiple channels:**
   - Direct email to decision makers (calibrated voice)
   - RFI/RFP responses on SAM.gov
   - ExampleVendor partner ecosystem (SOL.PARTNER connections)
   - SI partner referrals (Accenture, ExampleVendor, Leidos, Booz Allen)
   - Contract portals: Dice, Indeed, LinkedIn, ClearanceJobs, Upwork
5. **Track with CRM** — which companies researched, who contacted, what response

**Worst entry paths (proven to fail for C2C):**
- Direct cold email to Lockheed Martin COO or any C-suite at defense primes
- Formal supplier/vendor registration programs (individuals don't pass vetting)
- Roles requiring individual security clearance or personal ITAR cert

**Pulse discipline:**\n- Run a C2C opportunity hunter cron job every 3h searching for Solumina/MES\n  contracts on Dice, Indeed, LinkedIn, ClearanceJobs, SAM.gov\n- Only report real findings — no filler or spam\n- Each report should include: company, need, urgency, contact, approach path\n\n**MES/Solumina track:** See `references/mes-solumina-c2c-track.md` for the\nseparate MES/A&D outreach strategy, targeting rules, and research workflow.

### Tone
- Direct. No filler. No generic corporate language.
- The email should sound like a person, not a template.
- Sign-offs: match the user's actual signature ("Cheers, the operator" etc.)
- Openers: "Hey [Name]," not "Dear" or "To Whom It May Concern"

### Pipeline discipline
- Every draft gets reviewed by the user before sending (unless user
  explicitly waives this).
- Track what gets responses and iterate.
- It's a numbers game. One yes is all that's needed.
- "Imperfect action beats perfect inaction."

### BizDev pipeline pitfalls
- **Duplicate target entries break `save_interaction`**: If the BizDev MCP
  pipeline has duplicate company entries (same company under multiple IDs),
  `save_interaction` errors with "Multiple rows were found when one or none
  was required." The tool resolves by company name and fails when multiple rows
  match. **Workaround:** Use distinct company names (add a suffix like the ID
  number) or send via `send_email` directly (which works fine with non-unique
  names) and skip `save_interaction` logging. Ideally deduplicate the pipeline.
- **Outreach-to-contract conversion is tracked via email replies, not the
  pipeline**: The pipeline's `contracts_won = 0` and `total_outreach = 0`
  are starting points. After sending emails, track responses through Gmail,
  not through the BizDev MCP dashboard (which only updates when
  `save_interaction` succeeds).
- **Staffing firms actively hiring**: When researching targets, check job boards
  (Indeed, Dice, LinkedIn) for active Solumina MES openings. A live job posting
  is the strongest possible lead signal — they have already budgeted for the role.

## Infrastructure

### Gmail sending (SMTP via BizDev agent)
The BizDev agent has `bizdev_send_email` which sends through Gmail SMTP.
To set it up, the user needs:
1. 2FA enabled on their Google Account
2. An App Password (Google Account > Security > App Passwords)
3. The App Password is 16 characters with spaces. Strip spaces when using:
   `password.replace(" ", "")`

**MCP server env var configuration (required for bizdev_send_email tool):**
The `bizdev_send_email` tool reads `GMAIL_SENDER_EMAIL` and `GMAIL_SENDER_PASSWORD`
from `os.environ` at runtime. These MUST be set in the MCP server's environment,
which is defined in `config.yaml` under `mcp_servers.bizdev-agent.env`:
```yaml
mcp_servers:
  bizdev-agent:
    command: python
    args:
    - path/to/mcp_server.py
    env:
      DATABASE_URL: "..."
      GMAIL_SENDER_EMAIL: <your-email>@gmail.com
      GMAIL_SENDER_PASSWORD: xxxxxxxxxxxxxxxx  # 16-char App Password, no spaces
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    workdir: path/to/bizdev-agent
```

Adding these to `~/.hermes/.env` alone does NOT work — MCP server subprocesses
only see env vars explicitly configured in their `env:` block. Both locations
should be set for maximum compatibility.

**Direct execution fallback (when MCP tool env vars are stale):**
If the MCP server is already running without the Gmail vars and can't be
restarted, run the email sender directly via Python:
```bash
cd ${MY_REPOS}/auto-resume/bizdev-agent
export GMAIL_SENDER_EMAIL=<your-email>@gmail.com
export GMAIL_SENDER_PASSWORD=xxxxxxxxxxxxxxxx
python -c "
import os, sys; sys.path.insert(0, '.')
os.environ.update({'GMAIL_SENDER_EMAIL':'<your-email>@gmail.com','GMAIL_SENDER_PASSWORD':'xxxxxxxxxxxxxxxx'})
from app.agents.email_sender import get_email_sender
sender = get_email_sender()
result = sender.send(to='recipient@example.com', subject='Subject', body='Body')
print(result)
"
```

**Finding an existing Gmail App Password:**
The App Password may already be configured in `~/.config/himalaya/config.toml`
under `message.send.backend.auth.cmd` as a Python string with spaced characters.
Example: `"python -c \"import sys; sys.stdout.write('abcd efgh ijkl mnop'.replace(' ', ''))\""`
— the password is `abcdefghijklmnop` (16 chars, spaces removed).

### C2C Opportunity Hunter cron
Set up a cron job that runs every 3 hours, searching for C2C opportunities
matching the user's profile. The prompt should be self-contained and
reference the user's specific capabilities. Use `gpt-researcher` skill.

Key fields in the cron prompt:
- User's skills and experience
- Target company profile (small-mid, specific sector)
- Types of opportunities to search for
- What to include per lead (company, need, urgency, contact)
- Output format and length

### Local media monitoring
Set up a cron job that runs 3x daily searching local news for relevant
opportunities. Use the user's actual location (not assumed). Deliver to
the current conversation channel.

## Voice Red Flags (read these before sending any draft)

| Pattern | Looks Like | Fix |
|---------|-----------|-----|
| Em dash or hyphenated compound | "This tool -- which I built -- is fast" / "game-changer" | Use commas or periods. "Game changer" not "game-changer." |
| Generic opener | "I hope this finds you well" | Delete. Just start. |
| Filler signposting | "I am writing to introduce myself" | Delete the intro. Just write. |
| Hype language | "groundbreaking AI solution" | Say what it does, not how important it is |
| Rule of three | "innovation, inspiration, and impact" | Say it once. Don't triple it. |
| Partner-backup language | "We'd like you as our backup" or "We'll use you for overflow" | "We'd like to work with you on deals that fit your process." Never tell a business partner they are a secondary option. |
| Generic closer | "Looking forward to hearing from you" | Match their actual signature |
| Knowledge-cutoff disclaimer | "As of my last update..." | Delete. Just give the info. |
