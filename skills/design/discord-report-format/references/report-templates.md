# Report Templates

Concrete Discord-formatted examples for each report type. All follow the `discord-report-format` conventions: no blank lines between items, no em dashes, compact.

---

## 1. Pulse Brief (4-hour heartbeat)

```
🔵 **PULSE BRIEF** | Jun 18, 10:00 AM ET
━━━━━━━━━━━━━━━━━━━━━━
📊 **WORK STATUS**
✅ CRM sync | 142 records imported
🔄 Land parcel scoring | 5K of 75K processed
⚠️ Firefox BiDi disconnected | restarted OK

🌐 **INTEL**
**CVE-2026-1234** new RCE in libfoo | patch available
**Blogwatcher** 3 new posts from target blogs

━━━━━━━━━━━━━━━━━━━━━━
🔍 Checked Jun 18, 10:00 AM ET
```

## 2. Builder Email Watchdog

```
❗ **New Builder emails | 2 found**
━━━━━━━━━━━━━━━━━━━━━━
**1. Lennar**
📥 `Re: Land inquiry Lehigh Acres`
⏰ Thu, 18 Jun 2026 09:23:45 -0400
> Thanks for reaching out. We are interested in discussing your lots in Lehigh Acres. Please send over a list of available parcels.

**2. DR Horton**
📥 `FW: Vacant lot list`
⏰ Wed, 17 Jun 2026 14:12:33 -0400
> Can you send over the updated plat map and pricing for the Lehigh lots?

━━━━━━━━━━━━━━━━━━━━━━
🔍 Checked Jun 18, 12:34 PM ET
```

## 3. Morning Brief

```
☀️ **MORNING BRIEF** | Jun 18, 7:01 AM ET
━━━━━━━━━━━━━━━━━━━━━━
📊 **AGENDA**
🔄 Land sales | VA call queue ready for review
📬 2 new builder emails overnight | see watchdog report
✅ Cyber scan complete | no critical findings

🌐 **OVERNIGHT INTEL**
**Exploit-DB** new PoC for CVE-2026-5678
**Threat feed** 3 infostealer samples targeting M365 creds

━━━━━━━━━━━━━━━━━━━━━━
🔍 Checked Jun 18, 7:01 AM ET
```

## 4. Cyber Night Research

```
👻 **CYBER NIGHT RESEARCH** | Jun 18, 10:00 PM ET
━━━━━━━━━━━━━━━━━━━━━━
🔴 **CRITICAL**
**CVE-2026-9999** unauthenticated RCE in Apache Foo | PoC published
**CISA KEV** added 2 new actively exploited vulns

🟡 **NOTABLE**
New infostealer variant "StealC v3" targets browser creds
3 new ransomware gangs identified | 2 using leaked LockBit builder

🟢 **PATCHES**
libssl 3.4.2 released | fixes buffer overflow
Windows Update KB789012 | 6 security fixes

━━━━━━━━━━━━━━━━━━━━━━
🔍 Scanned Jun 18, 10:00 PM ET
```

## 5. Self-Healing Infra Pulse

```
💚 **INFRASTRUCTURE PULSE** | Jun 18, 2:00 PM ET
━━━━━━━━━━━━━━━━━━━━━━
✅ **SERVICES**
Hermes gateway | OK (2h uptime)
Camofox browser | OK (1h uptime)
Firefox BiDi | OK (port 9239)
Headroom proxy | OK (port 8787)

⚠️ **WARNINGS**
Disk C: | 58% used (342 GB free)

❌ **FAILURES** | none

━━━━━━━━━━━━━━━━━━━━━━
🔍 Probed Jun 18, 2:00 PM ET
```

## 6. Daily Cash-Flow Brief

```
💰 **CASH FLOW** | Jun 18, 8:00 AM ET
━━━━━━━━━━━━━━━━━━━━━━
📈 **BALANCES**
Checking | $12,450
Savings  | $48,200
Reserve  | $25,000

💳 **RECENT TRANSACTIONS**
Jun 17 | +$3,200 | Client payment MES consulting
Jun 16 | -$850  | VPS renewals
Jun 15 | -$200  | Domain registrations

📅 **UPCOMING**
Jun 20 | +$5,000 | Expected invoice payment
Jun 25 | -$1,200 | Monthly SaaS bills

━━━━━━━━━━━━━━━━━━━━━━
💰 Updated Jun 18, 8:00 AM ET
```

## 7. Weekly Intelligence Digest

```
📚 **WEEKLY INTEL DIGEST** | Jun 14-21
━━━━━━━━━━━━━━━━━━━━━━
🔥 **TOP STORIES**
**1. New Apache vuln impacts 60% of web servers**
   CVE-2026-1234 | PoC published | patch available in 2.4.63
**2. Ransomware group targets construction firms**
   BianLian variant | 3 US builders affected
**3. MES security advisory**
   Siemens issued advisory for SCALANCE X | update recommended

📊 **METRICS**
New CVEs this week | 142
Exploits added to CISA KEV | 8
Threat intel reports filed | 12

━━━━━━━━━━━━━━━━━━━━━━
📚 Compiled Jun 21, 10:00 AM ET
```

## 8. No-Change / Silent Delivery

Two patterns depending on the cron job type:

**no_agent scripts** — produce zero output. The scheduler sees exit code 0 with empty stdout and delivers nothing.

**Agent cron jobs** — respond with exactly `[SILENT]` as the entire output. The delivery system suppresses the message. Never combine `[SILENT]` with any other content.

Both patterns require a **freshness check first**: verify via session_search that nothing has changed since the last delivery before deciding to stay silent.

When a pulse job finds nothing noteworthy in a section, **omit the section** instead of writing "nothing new."

## 9. Daily Command Brief

```
🔵 **DAILY COMMAND BRIEF** | Jun 21, 11:20 AM ET
━━━━━━━━━━━━━━━━━━━━━━
📊 **SECTION HEADING (P0)**
**Item** | key detail, one line per item
**Next item** | detail with `filename` references
**Metric** | number, no blank lines between items

📬 **SECTION HEADING (P0)**
**Target** | count, status, action needed
Pipeline is stockpiled. Break the silence this week.

🔧 **INFRA & OTHER**
`tool-or-script` shipped with new feature
Other active project | latest status line
Data ingestion totals across sources

━━━━━━━━━━━━━━━━━━━━━━
🎯 **RECOMMENDED ACTIONS**
**Action 1** | specific step with timeframe, who does it
**Action 2** | concrete follow-up based on report findings
**Action 3** | scope or priority callout

━━━━━━━━━━━━━━━━━━━━━━
🔍 Checked: Mon DD, HH:MM AM/PM ET
```

The Command Brief differs from a morning brief or pulse in three ways:
- Multi-source data gathering: query open loops, bizdev/CRM dashboards, session history, and git logs — don't rely on a single script
- Priority-labeled sections (P0, P1 in the heading) to drive focus
- Always ends with Recommended Actions — this is the section the operator reads first
- Compact: every section heading has 3-5 items max. If a council lead has nothing actionable, omit the section
