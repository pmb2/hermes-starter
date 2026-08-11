# Hermes cron stdout delivery contract

For script-driven scanners (stock-sniffer, sports-betting ledger CLI, etc.).

## Job shape

```
name: <Scanner> — <Window>
schedule: <cron ET weekdays>
deliver: origin
workdir: ${USER_HOME}/Documents/github/<repo>
enabled_toolsets: ["terminal", "file"]
```

## Prompt template (self-contained)

```
Run the <Scanner> <mode> scan and deliver the Discord report only.

Working directory: ${USER_HOME}/Documents/github/<repo>

Commands (in order):
1. cd ${USER_HOME}/Documents/github/<repo>
2. python -m <pkg>.cli scan --mode <mode> --format discord

Rules:
- Your entire final message MUST be exactly the CLI stdout (the report body)
- If stdout is exactly [SILENT], reply with exactly [SILENT] and nothing else
- Do not add commentary, headers, planning text, or tool dumps
- On failure, print a short error line starting with ❌ <Scanner>
- Research aggregation only; never place trades
- Timeout budget: allow up to ~4 minutes for network collection
```

## Why this matters

- Cron delivery suppresses messages only when the **entire** body is `[SILENT]`
- Agent chatter before/after the report breaks Discord scannability and silent rules
- `workdir` + terminal/file toolsets keep the agent from wandering

## Weekend create → next weekday first fire

Creating jobs on Saturday schedules first run Monday (or next matching weekday). Say this explicitly in the user report.

## Multi-window pattern

Prefer **separate jobs per window** (morning/intraday/evening) over one job with internal clock logic — clearer ops, independent pause/resume, clearer failure attribution.

Stock Sniffer production IDs (2026-08-08):

| Window | Job ID |
|--------|--------|
| Morning Pre-Bell | `844f507d6460` |
| Midmorning | `3dfc14742709` |
| Midday | `287b0b558430` |
| Power Hour | `b21a4a58ee8d` |
| Evening Wrap | `8e50729579be` |
