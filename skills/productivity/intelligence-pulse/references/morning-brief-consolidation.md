# Morning Brief Consolidation (7:01 AM EST)

> Extracted from `productivity/intelligence-pulse` SKILL.md (v1.35.0 -> v1.36.0) on 2026-08-11.
> Owned by the `quiet-hours-pulse-digest` morning consolidation cron. The main SKILL.md carries a pointer to this file.

### Morning Brief Consolidation (7:01 AM EST)

**This is NOT the same as the Daily Cash-Flow Briefing.** The Morning Brief is the consolidation cron that runs at 7:01 AM ET, triggered by `quiet-hours-pulse-digest`. It synthesizes ALL overnight pulse findings (not just cash-flow) into ONE scannable report the operator reads first thing. It uses an **inverted workflow** compared to the standard pulse flow:

**Inverted Workflow:** Instead of Phase 1→2→3→...→9 (collect-first), the morning brief:
1. **Read the digest first** — the daily-digest/YYYY-MM-DD.md already has entries from overnight pulses (Self-Healing, Social Pulse Scan, the operator's Pulse, etc.). Read today's file AND yesterday's for full overnight-to-morning context.
2. **Verify independently** — don't trust the digest at face value. Independently check:
   - `docker ps` for still-restarting containers
   - git log across all repos for 48h activity
   - PIM DB direct query for new items
   - BizDev MCP dashboard
   - Open loops / decisions / risks from `_project/04-shared-memory/`
3. **Synthesize** — consolidate N digest entries + your own verification into a single brief.

**Delivery Format** — the operator's preferred structure for the 7:01 AM ET brief. Starts with a one-line summary, then 3-5 focused sections, ends with a question or recommendation. Total under **2000 chars**. Sections MUST reflect the operator's CURRENT stated priorities — non-static, adapt each run.

```
☀️ **Morning Brief — [Day, Date] · 7:01 AM EST**

📌 **Summary:** [one-line day summary — what changed overnight, if anything]

───

🏠 [P0 SECTION — named after the operator's #1 priority e.g. "Land Sales CRM"]
• [bullet item 1]
• [bullet item 2]

💰 [P0 SECTION — cash generation]
• [bullet item 1]
• [bullet item 2]

🖥 **Infrastructure Health**
• [one-liner per service: containers, GPU, disk, cron — pulse only, no deep dive]

⚡ **Key Decisions Needed Today**
• [ONE thing, maximum two — what the operator actually needs to decide, if anything]

📰 [INTELLIGENCE HIGHLIGHTS or OMIT]
• [only truly notable overnight items — omit section when nothing new]

───

✅ **Check:** HH:MM AM EDT | **Focus recommendation:** [one specific next action]
```

**Section rules (in priority order):**
1. **Name the #1 priority section after the operator's actual top goal** (currently `Land Sales CRM`). Don't use generic "Priority 1" — use the project name.
2. **Infrastructure must stay brief** — 3 lines max. Pulse only, no deep dive. Only flag CHANGES since last check.
3. **"Key Decisions Needed Today"** — this is NOT a focus recommendation. A decision needs a binary choice (yes/no, option A/B, go/no-go). Omit when nothing needs deciding.
4. **"Intelligence highlights"** — only truly notable overnight items. Omit the section entirely when there's nothing to report.
5. **"Cash generation"** — covers C2C outreach responses, RFPs, contract leads, email replies. NOT the same as BizDev pipeline analysis (which belongs in a separate pulse).
6. **End with a question or recommendation** — give the operator one concrete thing to decide or act on. Don't end with a platitude like "Have a productive day."

**Opening line rules:**
- Vary the opening emoji: ☀️, 🌅, 📋, etc. Don't use the same one every day
- Include the timestamp in the header: `· 7:01 AM EST`
- The one-line summary below the header MUST be concrete, not generic. Bad: "Overnight was quiet." Good: "Overnight quiet. Land Sales CRM is stalled at 3 weeks stale — research complete, no lot matching yet."

**When to stay SILENT:**
- If the operator explicitly set no cron for today or the job fires on a non-business day, respond `[SILENT]`
- If nothing at all has changed across all sections and no decisions are needed, respond `[SILENT]`
- Use `[SILENT]` for weekend runs when the operator is not working — but check git/email first in case there WAS weekend activity
- Never combine `[SILENT]` with content text

**Pitfalls specific to this cron:**
- **Sections drift with the operator's priorities.** If the operator says "Bookends is back on" midway through the month, the morning brief must shift immediately — move the project into the P0 position, rename sections accordingly. Don't keep reporting on last month's format.
- **Don't let credit outages or cron gaps fill the brief.** A 7-day outage in June doesn't need re-explaining. The brief covers TODAY. Past incidents belong in a retrospective, not the morning read.
- **The format is compact, not comprehensive.** 5 sections max. If everything is important, nothing is. Choose the 3-5 things the operator cares about most right now.
- **Don't guess at repo locations.** This session found `~/ghl` doesn't exist. The Land Sales CRM may be hosted elsewhere or not yet started. If a repo path is unknown, say it plainly rather than fabricating a status.
- **Cross-reference the digest's "no user activity" claims.** In cron context, all visible sessions are cron sessions, so any "no user activity in N days" from the digest is likely a false positive. Check git log for human-authored commits as ground truth.
- **Digest-first means you MUST verify.** Don't repeat digest claims without checking. Always run your own `docker ps` / git log / sqlite3 queries.
- **Don't let digest bloat inflate delivery.** Extract only the high-signal findings from each digest entry. The user doesn't need the output of all 6 overnight agents — they need the 5 points that matter.
