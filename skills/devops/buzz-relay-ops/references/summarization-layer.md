# Summarization Layer — Buzz Agent Fleet

Architectural pattern for preventing the Chief of Staff from being overwhelmed by
raw message volume across 30+ channels. Deployed in production with a 47-agent
fleet across 58 Buzz channels.

## Problem

A Chief of Staff agent monitoring 30+ Buzz channels sees hundreds of messages daily.
Without summarization, important signals drown in noise. The CoS needs to be "always
up to date with the data needed and able to easily get whatever it needs" without
reading every message.

## Solution: Three-Tier Summarization Pipeline

```
TIER 1: Lead Summaries (daily, per-channel)
    Each Council Lead posts a structured summary to their channel
    Format: "Daily Report — [Role] — [Date]"
    Sections: ✅ Completed, 🔄 In Progress, 🚫 Blocked, 🔴 Needs the operator, 📊 Metrics
    Rules: be specific, include agent names, keep under 15 lines, delete empty sections

TIER 2: CoS Compilation (daily, 9am cron)
    CoS cron reads all lead summaries from last 24h
    Cross-references for duplicate topics, stale loops, missed decisions
    Checks infrastructure: bridge PID, OmniRoute health, active crons
    Compiles into Daily Command Brief → #admin
    the operator sees: top 3 priorities, cash flow, open loops, risks, decisions needed

TIER 3: On-Demand Deep Dive
    the operator or CoS can @mention any lead for full detail on any item
    CoS has full channel visibility — reads raw messages when needed
    CoS can query raw relay events for historical context
```

## Daily Command Brief Format

```markdown
# Daily Command Brief — Mon Aug 10 2026

## 🔴 Needs the operator (decisions required)
| # | Domain | Decision | Deadline |

## 🟡 Open Loops (in progress)
| # | Domain | Item | Owner | ETA |

## 🟢 Completed (since last brief)
| Domain | Item |

## 🚫 Blocked / At Risk
| Domain | Item | Blocker | Action Needed |

## 💰 Cash Flow Snapshot
| Metric | Value |

## 📊 System Pulse
| Check | Status |

## 🧠 Intelligence Highlights
- Cross-domain patterns surfaced during channel scan

## 📌 Today's Top 3 Priorities

## 🔍 Cross-References
| Connection | Domains | Significance |
```

## Channel Prioritization Tiers

The CoS doesn't scan all channels equally. Prioritize by tier:

| Tier | Channels | Scan Freq |
|------|----------|-----------|
| P0 | #admin, #development, #engineering, #revenue, #supervisor | Every scan |
| P1 | #cybersecurity, #intelligence, #research, #legal, #finance, #investing, #betting | Every scan |
| P2 | #health, #content, #media, #operations, #market-lead, #career, #tax | Every other scan |
| P3 | #skills, #docs, #api-docs, #testing, #releases, #monitoring, #automation | Daily only |

## CoS Cron Jobs

| Cron | Schedule | Purpose | Silent? |
|------|----------|---------|---------|
| `cos-morning-brief` | 0 9 * * * | Compile lead summaries → Daily Command Brief → #admin | No (always posts) |
| `cos-channel-scan` | 0 */4 * * * | Scan all channels for urgent flags | Yes (only posts if 🚨) |
| `cos-open-loop-check` | 0 12 * * * | Cross-reference decision log, flag stale items | No |
| `cos-pulse-check` | */30 * * * * | Infrastructure health: bridge PID, OmniRoute, crons | Yes (only if 🔴) |

## Lead Summary Rules

1. Be specific — "Deployed site rebuild to staging" not "Made progress on site"
2. Include agent names so CoS knows who to follow up with
3. If a section has nothing, delete it entirely
4. Keep under 15 lines total — CoS compiles N of these
5. Post in your team channel, not as a reply

## Implementation Files

- `templates/cos-daily-command-brief.md` — full brief template
- `templates/lead-daily-summary.md` — lead report template
- `prompts/cos-morning-brief.md` — CoS 9am cron prompt
- `prompts/cos-channel-scan.md` — CoS 4h silent scan prompt
- `prompts/lead-daily-summary.md` — lead cron prompt
- `docs/checklists/buzz-migration-verification.md` — 70-item 5-phase checklist

## Key Design Principles

1. **Summarization is lead-driven, CoS-compiled.** Each lead only summarizes their domain.
   CoS only compresses and cross-references. This distributes the work.
2. **CoS can always go deep.** The brief is a starting point, not a wall. CoS retains
   full channel visibility and can query raw relay events.
3. **Silent when healthy.** Channel scans and pulse checks produce no output unless
   something is wrong. This prevents notification fatigue.
4. **Cross-domain pattern detection.** The CoS brief explicitly flags the same topic
   appearing in multiple channels — connections the operator would miss.
