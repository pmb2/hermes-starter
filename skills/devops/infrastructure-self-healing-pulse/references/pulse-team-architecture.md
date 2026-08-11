# Pulse Team Architecture

The natural evolution of a self-healing pulse cron job into a dedicated agent team. When the monitoring scope grows beyond what a single cron job can handle, provision a team:

## Team Roles

| Agent | Role | Cadence | Mission |
|-------|------|---------|---------|
| **Vigil** | Watcher | Every 15m | Infrastructure heartbeats — is everything running? |
| **Chronicle** | Tracker | Every 4h | Project progress — are we moving forward? |
| **Helix** | Healer | Every 4h | Self-healing — what broke and did we fix it? |
| **Muse** | Curator | Every 6h | Intelligence — what should the operator know? |

## Channel Structure (Spacebar)

| Channel | Purpose |
|---------|---------|
| `#pulse-alerts` | 🔴 Real-time health alerts (Vigil → the operator, Helix) |
| `#pulse-status` | 🟢 Every-heartbeat status summary |
| `#pulse-report` | 📋 Chronicle's project progress |
| `#pulse-intel` | 🧠 Muse's intelligence brief |
| `#pulse-internal` | Team coordination |

## Data Flow

```
Vigil (15m) ──health──▶ Helix (4h) ──fixes──▶ the operator
   │                      │
   └──State───────────────┘
        │
   Chronicle (4h) ──progress──▶ the operator
        │
   Muse (6h) ──intel──▶ the operator

All → MemPalace (shared memory)
```

## Escalation Rules (from AGENTS.md)

| Severity | Response | Escalate To |
|----------|----------|-------------|
| 🔴 Critical | Helix fixes immediately, alerts the operator | the operator (immediately) |
| 🟡 High | Helix investigates, Vigil monitors | Helix + the operator (within 1h) |
| 🟢 Medium | Logged, scheduled for next maintenance | None (tracked) |
| 🔵 Low | Added to digest | None (Muse curates) |

Any service down for >2 consecutive Vigil checks → auto-escalate to 🔴.
Priority misalignment detected >24h → Chronicle flags to the operator.
Playbook fails 3x → escalate to the operator (need human decision).
Infrastructure topology change detected → ask the operator for confirmation.

## Provisioning

See `teams/pulse/cron-config.md` in the agent-fleet repo for exact cron prompt templates and skill assignments per agent profile.

Location: `${MY_REPOS}/agent-fleet/teams/pulse/`
