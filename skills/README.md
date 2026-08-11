# Skills

**~276 curated, privacy-scrubbed skills** — the reusable half of a heavily-customized
production library. Skills are markdown documents with YAML frontmatter that teach the
agent how to do specific things: exact commands, pitfalls, and workflows.

## How they're organized

```
skills/
├── autonomous-ai-agents/   # hermes-agent, claude-code, codex, opencode, routing
├── creative/               # p5js, sketch, excalidraw, manim, humanizer, design
├── curation/               # skill library health, audits, find-skills
├── data-engineering/       # market scanners, sports pipeline, FOSS mapping
├── data-science/           # jupyter live kernel
├── design/                 # discord report formatting, UI/UX intelligence
├── devops/                 # self-healing, cron watchdogs, MCP servers, browser stealth,
│                           #   gateways, backups, traefik, tor, vps, hermes ops
├── email/                  # himalaya IMAP/SMTP
├── fal-ai/                 # media generation catalogs + pipelines
├── finance/                # investing framework
├── gaming/                 # emulator strategy bots
├── github/                 # PRs, issues, code review, repo management
├── health/                 # supplement stacks, medical research
├── integrations/           # knowledge MCP
├── legal/                  # privacy rights, reputation, watchdog
├── mcp/                    # MCP client, remote desktop, mempalace
├── media/                  # youtube, spotify, gifs, voice memos, video playbooks
├── mlops/                  # fine-tuning, llama.cpp, vector DBs, W&B, DSPy, SAM, outlines
├── note-taking/            # obsidian vault
├── operations/             # chief of staff, digital product, status checks, pulses
├── productivity/           # gmail/calendar, notion, linear, airtable, pdfs, xlsx, maps
├── research/               # arxiv, polymarket, deep research, gpt-researcher
├── security/               # OSINT suite, domain recon, threat intel, compliance outreach
├── site-generation/        # competitive site cloning
├── smart-home/             # philips hue
├── social-media/           # brand manager, postiz automation
├── software-development/   # MCP building, TDD, debugging, voice agents, browser tools
└── web-development/        # static sites, service sites, gsap, scroll-world
```

## What was excluded and why

Business-specific and personally-identifying skills were **not** shipped. Missing
categories (and how to get equivalents):

- **Real estate / land wholesale / property** — the operator's venture pipelines
- **Job-agent, bizdev, lead-gen for specific markets** — ditto
- **Website-landlord / local-service-sites** — business product skills
- **AI-sharp / TAC odds** — betting venture
- **PIM (personal intelligence) pipelines** — personal data infrastructure
- **gstack / hub packs** — reinstall from the hub: `hermes skills install <id>`

## Using skills

- Skills load automatically when relevant (each has a `description` trigger).
- Force-load one: `/skill <name>` in chat.
- Browse what's installed: `hermes skills list`
- The agent can **save new skills** from its own problem-solving — that's how the
  library grows. Each shipped skill is a template for how to structure yours.

## License note

Skills retain any authorship metadata in their frontmatter. The kit itself is MIT;
individual skills carry their own provenance where marked.