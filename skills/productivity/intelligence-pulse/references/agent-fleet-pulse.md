# Agent-Fleet Pulse Integration

How the `intelligence-pulse` skill powers the Social Media Team's Pulse agent.

## Location

- **Pulse agent profile**: `agent-fleet/teams/social-media/pulse/` (SOUL.md, AGENTS.md, SKILLS.md)
- **Scan script**: `agent-fleet/teams/social-media/pulse/tooling/pulse_scan.py`
- **State files**: `.last_pulse_scan.json` (timestamps + seen IDs), `.pulse_history.json` (last 20 reports)

## Cron Chain

| Cron | Schedule | Script Flag | Description |
|------|----------|-------------|-------------|
| Live Scan | Every 4h | (no flag) | Raw data collection, deduplication, prev-report context |
| Morning Wrap | 06:00 daily | `--report-type morning --history 3` | Loads overnight scans, comprehensive morning brief |
| Evening Wrap | 18:00 daily | `--report-type evening --history 5` | Aggregates all today's scans, day-in-review |

## YouTube Transcript Data Structure

The file `youtube_transcripts.json` (at `${USER_HOME}/FireFox-Phantom-MCP/`) contains the full YouTube library with summaries:

```json
{
  "extracted_at": "2026-05-30T00:05:58",
  "total_videos": 985,
  "with_transcripts": 478,
  "without_transcripts": 507,
  "videos": [
    {
      "video_id": "zaXKQ70q4KQ",
      "title": "The Man Who Took LSD and Changed The World",
      "channel": "Veritasium",
      "url": "https://www.youtube.com/watch?v=zaXKQ70q4KQ",
      "summary": {
        "one_liner": "...",
        "topics": ["AI_Agents", "Business_Development"],
        "insights": ["Key insight 1", "Key insight 2"],
        "actionable": ["Action to take"],
        "relevance": ["AI_Engineering", "Business_Development"],
        "importance_rating": 10,
        "_summarized_at": "2026-05-29T20:39:26"
      }
    }
  ]
}
```

Key fields for content mining:
- `summary.one_liner` — A 1-sentence takeaway
- `summary.topics` — Topic tags
- `summary.insights` — Key learnings (use these for thread content)
- `summary.actionable` — Verifiable actions (use these for call-to-action posts)
- `summary.relevance` — Cross-source relevance tags
- `summary.importance_rating` — 1-10 scale (7+ is content-worthy)
- `_summarized_at` — When it was summarized (for new-item tracking)

As of May 30, 2026: 463 videos have populated `summary` fields (the rest have transcripts but no AI summary yet).

## Pulse Scan Script

`python pulse_scan.py [--quick] [--report-type morning|evening] [--history N]`

Output: JSON to stdout with:
- `timestamp`, `date`, `period`, `report_type`
- `blogwatcher[]` — RSS items (skipped in --quick mode)
- `youtube[]` — New summarized videos (sorted by importance, deduped by video_id)
- `pim[]` — New PIM DB items (skipped in --quick mode)  
- `trends{}` — Items grouped by trend category (AI_Agents, Security, Business, etc.)
- `content_picks[]` — Top 5 items with title, one_liner, pillar, suggested_angle, url
- `prev_reports[]` — Last N reports for context (loaded from `.pulse_history.json`)
- `summary{}` — Total counts, pillar distribution, trending keywords, top trend

## Agent Profile Audit Pattern

Before deploying any fleet agent, audit its SOUL.md and AGENTS.md for **aspirational dependencies**:

1. Scan AGENTS.md "Data Sources" or "Tools" section for any external API, service, or integration
2. For each: is it actually configured? (credentials exist? service running? endpoint reachable?)
3. Build a status table in AGENTS.md:
   ```markdown
   | Source | Status | Notes |
   |--------|--------|-------|
   | X/Twitter API | ❌ Not wired | Aspirational — no credentials |
   | blogwatcher | ✅ Live | RSS feeds, 50+ sources |
   ```
4. If a source is not wired, either remove it (no false advertising) or note "Not wired — aspiration only"
5. Always prefer existing live sources over aspirational ones:
   - blogwatcher (RSS) is live → use it instead of claiming X API
   - YouTube transcripts are live (463 summaries) → mine them instead of fabricating trend data
   - PIM DB is live (1500+ items) → query it instead of simulating intelligence

## History File Format

`.pulse_history.json` stores the last 20 reports for context chaining:

```json
[
  {
    "timestamp": "2026-05-30T04:41:22Z",
    "report_type": "morning",
    "summary": { "total_new": 463, "top_trend": {...} },
    "content_picks": [ { "title": "...", "url": "..." } ],
    "trends": { "AI_Agents": [...], "Security": [...] }
  }
]
```
