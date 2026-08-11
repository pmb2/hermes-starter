# Infrastructure Reconstruction — Quick-Start Checklist

> Copy this template and fill in the blanks. Delete phases that don't apply.

## Before You Start

- [ ] Windows 10/11 installed and updated
- [ ] Git installed: `winget install Git.Git`
- [ ] Python 3.11+ installed: `winget install Python.Python.3.11`
- [ ] Node.js 20 LTS installed: `winget install OpenJS.NodeJS.LTS`
- [ ] Docker Desktop installed: `winget install Docker.DockerDesktop`
- [ ] pip updated: `python -m pip install --upgrade pip`

## Phase 1 — Config Repo

- [ ] Config repo cloned: `git clone <repo-url> ~/Documents/github/hermes-config`
- [ ] Supporting repos cloned (list: ______________________________)
- [ ] Path migration complete (old user/drive → new user/drive)
- [ ] Setup script run: `bash scripts/setup.sh`

## Phase 2 — Core Install

- [ ] Hermes installed: `curl -fsSL https://hermes-agent.nousresearch.com/install | sh`
- [ ] Verified: `hermes --version && hermes doctor && hermes doctor --fix`
- [ ] Config files copied (config.yaml, .hermes/config.yaml, jobs.json, model_config.json)
- [ ] `.env` created with all keys

## Phase 3 — Infrastructure Services

- [ ] OmniRoute started on port _____
- [ ] Trilium Docker running on port _____
- [ ] Postgres Docker running on port _____
- [ ] Logseq graph directory created
- [ ] Buzz relay running (if applicable)
- [ ] MemPalace installed and initialized
- [ ] Camoufox installed (if using stealth browser)
- [ ] FAL.ai key configured

## Phase 4 — MCP Servers

- [ ] Dependencies installed: `pip install mcp fastmcp mempalace tradingview-mcp`
- [ ] Knowledge MCPs wired (logseq + trilium)
- [ ] Browser MCPs wired (firefox-devtools, firefox-phantom)
- [ ] Finance MCPs wired (tradesignals, tradingview)
- [ ] Dev tool MCPs wired (git-stars, gpt-researcher, personal-intelligence)
- [ ] Intelligence MCPs wired (bizdev-agent, job-agent)

## Phase 5 — Profiles

- [ ] All _____ profile directories created
- [ ] Critical profiles working (default, development-lead)
- [ ] Council profiles restored (___ profiles)
- [ ] Team profiles restored (___ profiles)
- [ ] Specialist profiles restored (___ profiles)

## Phase 6 — Scripts & Cron

- [ ] All scripts copied to `~/AppData/Local/hermes/scripts/`
- [ ] Bulk dependencies installed
- [ ] Cron guardian registered
- [ ] Model watchdog registered
- [ ] Firefox health watchdog registered
- [ ] Intelligence pipelines registered
- [ ] YouTube WatchLater registered

## Phase 7 — Verification

- [ ] `hermes doctor` passes
- [ ] API connectivity verified (DeepSeek, OpenRouter, OpenCode Go)
- [ ] Docker services healthy and responding
- [ ] MCP servers connected (`hermes mcp list` + `hermes mcp test`)
- [ ] Knowledge bases accessible
- [ ] Cron jobs registered (`hermes cron list`)
- [ ] Profile switching works
- [ ] Skills library populated (`hermes skills list`)
- [ ] Script syntax valid (`python -m py_compile` each script)
- [ ] End-to-end conversation test passes
- [ ] (Optional) VPS stack deployed and verified
