# Hermes Starter Kit

A privacy-scrubbed, self-contained starter kit for [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.

Clone it, fill in your own tokens, run one script — and you get a working multi-agent
Hermes deployment with:

- **Discord gateway** — channel-specific agent personas that auto-respond in their channels
- **Buzz bridge** — a local [Buzz](https://buzz.xyz) / Nostr relay bridge where each agent
  has its own identity (optional)
- **~280 curated skills** across devops, software development, creative, security,
  research, MCP, and more
- **Reusable infrastructure scripts** — cron guardian, self-healer, model watchdog,
  log rotation, provider recovery — the things that keep a 24/7 agent healthy
- **Cron seed jobs** — heartbeat pulses, guardian sweeps, and report jobs you can
  extend with your own pipelines
- **2 custom plugins** — silent provider self-healing and dual-tier model routing
- **Prompt + template library** — daily briefs, channel scans, lead summaries

The kit contains **no personal data, no credentials, no private accounts, and no
business-specific pipelines**. It is the tooling layer from a heavily-customized
production deployment, sanitized for public distribution.

> ⚠️ **What this is NOT:** this is not your operator's personal configuration. It's the
> reusable machinery. You bring your own model keys, Discord bot, channels, and ideas.

---

## Quick Start

```bash
git clone https://github.com/pmb2/hermes-starter.git
cd hermes-starter
bash scripts/setup.sh            # installs config, skills, scripts, plugins into Hermes home
```

Then follow **[BOOTSTRAP.md](./BOOTSTRAP.md)** for the full zero-to-running walkthrough
(LLM provider → Discord bot → gateway → personas → cron).

---

## Repository Layout

| Path | What it is |
|------|-----------|
| [`config/config.example.yaml`](./config/config.example.yaml) | Full Hermes config with env-var placeholders — copy to your Hermes home and edit |
| [`config/agent-model-overrides.example.yaml`](./config/agent-model-overrides.example.yaml) | Per-agent model routing manifest (preview of a multi-agent fleet) |
| [`scripts/`](./scripts/) | Reusable automation: buzz bridge, watchdogs, self-healing, log rotation |
| [`scripts/setup.sh`](./scripts/setup.sh) | One-command installer |
| [`skills/`](./skills/) | Curated generic skill library (~280 skills) |
| [`prompts/`](./prompts/) | Cron prompts: daily briefs, channel scans, lead summaries |
| [`templates/`](./templates/) | Report templates (command brief, lead summary) |
| [`profiles/`](./profiles/) | Example `AGENTS.md` for a Chief-of-Staff profile |
| [`gateway/`](./gateway/) | Discord + Buzz gateway setup guides |
| [`cron/`](./cron/) | Seed cron jobs + how cron works |
| [`.env.example`](./.env.example) | Every environment variable you need, with zero values |

---

## What's Excluded (deliberately)

- **`hermes-config`** — the operator's private living config/docs repo (private on GitHub)
- **`hermes-system-backup`** — the operator's private disaster-recovery backup
- Memories, session history, chat logs, state databases
- Business-specific skills & pipelines (land wholesale, job hunting, betting, property,
  website-landlord, etc.) — those are the operator's ventures, not reusable tooling
- GitHub-accessible skill packs (gstack, etc.) — install those from the skills hub instead:
  `hermes skills install <id>`

---

## License

MIT — see [LICENSE](./LICENSE). Skills retain their own authorship where marked.