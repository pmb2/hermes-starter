# Watchdog Alert Triage (worked example, Aug 2026)

Pattern for pulses when a watchdog/monitor reports persistent failures. Never report raw failure counts as an outage — triage in this order:

1. **Streak age** — `grep -n "found.*failure" logs/<watchdog>.log | head -3`. A streak that predates today is a pre-existing false positive, not a new incident. Compare against the log's first line.
2. **Reproduce the exact failing check manually** in your shell. Exit 0 + real output means the watchdog's own wrapper is broken (JSON parse choking on warning lines, missing env in its context), not the service.
3. **Verify actual state independently** — `docker compose ps --all` / `docker ps -a`. Up + healthy containers beat a monitor's "missing service" claim.
4. **Check the alert-delivery channel itself** — a watchdog whose notification path is dead (SMTP "Authentication required", mailbox unavailable) sends NOTHING when real failures hit. A monitor you can't hear is worse than no monitor. This is usually the true actionable incident hiding underneath the false positive.

## Worked example: ghl agency-comms-watchdog (Aug 4, 2026)

- Symptom: `runtime/agency-comms-watchdog.status.json` → `ok:false`, 25 failures every 5 min: "Command threw: docker compose ps --all --format json" + "Critical service is missing: postgres / redis / agency-faster-whisper / ...".
- False-positive root cause: compose emits `level=warning ... variable is not set. Defaulting to a blank string.` lines that break the watchdog's JSON parse → every compose-based check "fails". Streak predates today (present since Jun 15 in the log).
- Reality: `docker compose ps --all` shows postgres/redis/calcom/fonoster/authentik/budibase all Up (healthy). Stack is fine.
- Hidden real incident: notification email failing since Aug 3 12:10 — SMTP "Mailbox unavailable. The server response was: Authentication required" (497 failed sends by Aug 4 19:26). Watchdog cannot alert anyone → fix SMTP creds.
- File gotchas: status/last-failure JSONs carry a UTF-8 BOM — parse with `encoding='utf-8-sig'`. Watchdog log uses PowerShell-style timestamps `[2026-08-04 19:26:05]`.

## Reporting rule

One line for the known false positive ("known since <date>, stack verified healthy") — do NOT relitigate it every cycle. Flag the dead notification channel as the actionable item, plus any NEW deltas (uncommitted config work, alert-channel status).
