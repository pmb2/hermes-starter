# Fleet Manager: Core Council + On-Demand Teams

## Architecture

The fleet splits into two tiers to save resources (~3-4GB RAM with all 44 bots online, ~700MB with just core 9):

```
fleet-manager.py (CLI tool, not a daemon)
├── python fleet-manager.py deploy   → Kill ALL bots, start just core 9
├── python fleet-manager.py status   → Show live status of all bots
├── python fleet-manager.py activate <team>  → Start a team's bots
└── python fleet-manager.py deactivate <team> → Stop a team's bots
```

**Core Council (9 bots, always-on):**
- chief-of-staff — Central CoS
- technology-lead — Dev crew lead
- growth-lead — Sales/Solumina lead
- intelligence-lead — OSINT/Pulse lead
- treasury-lead — Budgeting
- counsel-lead — Legal
- compliance-lead — Tax
- portfolio-lead — Trading/Scouts lead
- operations-lead — Ops/Health lead

**Standby Teams (35 bots, activated on-demand):**

| Council Lead | Team | Bots |
|-------------|------|------|
| technology-lead | technology (8) | development-lead, dev-lead, docs-lead, docs-lead-dev, qa-lead, skills-lead, integration-lead, automation-lead |
| intelligence-lead | intelligence (11) | history-lead, pulse, security-lead, cyber-osint, threat-lead, media-lead, creative-lead, writing-lead, nova, notes, lane |
| portfolio-lead | investment (9) | odds-lead, data-lead, verifier, assistant, product-lead, admin, people, analyst, scout |
| growth-lead | revenue (2) | manufacturing-lead, ai-agency |
| operations-lead | operations (4) | wellbeing-lead, health-performance, market-lead, outreach-lead |
| counsel-lead | legal (1) | legal-case-support |
| treasury-lead | (none) | — |
| compliance-lead | (none) | — |

## Team Activation

Each council lead activates their team when they need specialist assistance:

```bash
# From relay-pool directory:
python fleet-manager.py activate intelligence   # 11 intel bots come online
python fleet-manager.py deactivate intelligence # Kill those 11 bots
```

## Implementation

The script lives at `${MY_REPOS}\Documents\github\relay-pool\fleet-manager.py`.

It uses `ctypes.windll.kernel32.OpenProcess` for Windows-safe PID checking (replaces `os.kill(pid, 0)` which fails on Windows). Each bot is killed via the PID in its `gateway_state.json`.

New bots are started with `subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP` for silent daemonization.
