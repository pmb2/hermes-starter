## Common stale entries to look for:

- YT Animation: roadmap says "Research phase" but actual pipeline is in beta with Docker Compose, full orchestrator, production docs, and active pipeline commits (scene_assembler, scene_generator, production_assembler) — past research entirely

- **TwitchFarm**: roadmap says "Not started" but the repo at `${MY_REPOS}/TwitchFarm/` contains a working account creator with browser automation, email verification, Docker setup, and Flask templates. Code exists with ~20 files. The "Not started" status is inaccurate — check whether it was intentionally parked or just undocumented.

- Bookends: roadmap says "In development" but the repo can go weeks without commits — check actual commit activity to confirm

- P-level drift: the pulse prompt (this skill) is maintained more frequently than monthly-priorities.md — trust the pulse prompt's P-levels as more current



### Phase 8: Deliver the Pulse



**DELIVERY ROUTING — CRITICAL RULE: Pulse deliveries must NOT go to the user's active conversation channel.** the operator explicitly stated that pulse/heartbeat reports are distracting when they arrive in the #command channel where he's actively strategizing.



**Correct routing:**

1. Deliver the full pulse report to **#pulse-feed** (or equivalent dedicated intelligence channel).

2. The Chief of Staff (if different from the pulse agent) receives a **one-line pointer**:  

   `"📡 Oracle: Pulse in #pulse-feed — 3 articles for [project], 2 blogwatcher hits, 1 BizDev signal"`

3. the operator can go to #pulse-feed to read the full report and discuss with the Intel Lead.

4. Never include raw pulse dumps, long article excerpts, or multi-paragraph analyses in #command.



**When delivering to #pulse-feed:**



**When delivering to #pulse-feed:** use this format:



**Concise, scannable, under 2000 characters** — the operator reads pulses in a separate channel, not the strategy channel.



**🚫 SILENT ON NO CHANGE — CRITICAL RULE (Phase 0 overrides this entire section):** If no new items, no activity changes, and no BizDev signals exist since the last pulse, produce NO output. Do NOT send "nothing new to report" — that's been explicitly rejected as spam. Only deliver when there's actual news. The Freshness First Phase 0 workflow controls this: if session_search shows your last output covered the same ground, do not repeat it.



**🔗 Every research highlight MUST include a digest link.** Each intelligence finding, blogwatcher pick, or research result that appears in the "Research Highlights" section must include a link back to the source digest file so the operator can click through for full context.



Format for each highlight:

```

- [title] — relates to [project] — [1-line why it matters] 📄 [Digest](file:///${MY_REPOS}/Documents/github/_project/daily-digest/YYYY-MM-DD.md)

```



The `📄 [Digest](...)` suffix uses a local `file://` URL pointing to the daily digest file where the finding was logged. This works on the operator's machine because the `_project` repo is checked out at `${MY_REPOS}/Documents/github/_project/`. If the finding came from a specific pulse run that appended to the digest, reference that same file. If the finding was NOT logged to the digest (e.g., it came from a direct query), note `🔍 [Source](<source-url>)` instead.



This rule applies to ALL pulse deliveries that include research highlights — Morning Brief, Evening Brief, Pulse Scan, Weekly Roundup. Every item that gets reported as intelligence must have a clickable provenance link.



**Delivery format:**



```

[Systems check] — all healthy / [N] issue(s)



Intelligence: [N] new item(s)

- [Most relevant title] — relates to [Project] — [1-line why it matters]

- [Other items with project attributions]

- [N] uncategorized



Recent Activity (last [timeframe])

| Project | Status |

|---|---|

| [P0 Project A] | [recent commit summary] |

| [P0 Project B] | [stale since date] |

| [P1 Project C] | [last known state] |



BizDev: [N] targets . [N] contacts . [N] outreach sent . [N] contracts won

[Flag if 0 outreach or stalled]



Focus: [ONE specific thing to work on next]



Quick Wins (<15 min):

- [Actionable task 1]

- [Actionable task 2]



ADHD Check: [Prevent sprawl — 1-line recommendation]

```



**Output parsing quirk**: `intelligence_collector.py check-new` emits interleaved [INFO] log lines and a final JSON block. The JSON block is at the end of the output with `{ 'email': {...} }` or similar top-level keys. Extract it by finding the last line that starts with `{` — do not rely on a clean JSON-only stdout.



**Vary the emoji palette and sentence rhythm each pulse** — the user notices robotic repetition. Alternate between emoji sets and vary opening lines.



### Phase 8a: Boss Radar Scoring & Action Tiers



Every finding surfaced in a pulse should carry a relevance score and action tier — the "boss radar" system. This gives the operator immediate context for triage: does this need action now, just watch, or background only?



**Relevance Score (0.0 - 1.0)**

Assigned per finding based on direct applicability to the operator's stack, current projects, or known pain points:

- **0.70+** — Directly applicable right now. A tool to install, a model to try, a technique that solves a known problem, an opportunity with immediate ROI.

- **0.40-0.69** — Relevant but not urgent. Worth monitoring. New framework, promising paper, pricing change worth knowing about.

- **Below 0.40** — Background signal. Skip in delivery.



**Action Tier (derived from score)**

- **TIER 1 (ACT NOW)** — Score >= 0.70. Has direct near-term impact. Install, try, switch, read, act.

- **TIER 2 (WATCH)** — Score 0.40-0.69. Worth monitoring. Could become important. Doesn't need action yet.

- **TIER 3 (NOTE)** — Score < 0.40. Background context. Not surfaced in delivery.



**Delivery rule:** Only surface TIER 1 and TIER 2 findings in pulse output. If nothing scores above 0.40 and nothing is actionable, stay SILENT.



### Phase 8b: Auto-Action on TIER 1 Findings



When a TIER 1 finding has an executable action, execute it — don't just report it. Install the tool, clone the repo, download the paper, log the opportunity, submit the form. the operator's explicit directive (June 2026): \"taking action in automatically implementing, downloading, installing, and setting up anything that hits tier one.\"



**Actions by finding type:**



| Finding Type | Auto-Action |

|--------------|-------------|

| **arXiv paper** (URL contains arxiv.org/abs/) | Download PDF to `${MY_REPOS}/Documents/research/papers/<id>.pdf` via curl |

| **GitHub repo** (URL contains github.com/) | `git clone --depth=1` to `${MY_REPOS}/Documents/github/<name>`, then `pip install -e` if setup.py/pyproject.toml exists |

| **CLI tool / package** | `pip install` or `npm install -g`, run smoke test |

| **GovCon opportunity** | Log to `${MY_REPOS}/Documents/research/opportunities.md` with timestamp and source URL |

| **New AI model with available weights** | Check if pullable via ollama/huggingface-cli and run it |

| **Agent framework / coding tool affecting stack** | Install and run quick import smoke test |



**Dedup:** Track already-executed actions in a state file (auto_action_state.json) by fingerprint. Never re-execute the same action.



**Script reference:** The `scripts/auto_action_handler.py` (at `${USER_HOME}/AppData/Local/hermes/scripts/auto_action_handler.py`) implements this for the monitoring pipeline — it's a no_agent cron that reads latest.json + history.jsonl, pattern-matches TIER 1 findings, and executes the appropriate action. For LLM-driven pulses (AI Ecosystem), the agent itself should take action during synthesis using its terminal tools.



**Pitfalls:**

- Respect rate limits on external APIs (arXiv 1 req/3s, GitHub 60 req/hr unauthenticated)

- Don't re-clone repos that already exist (check dir first)

- Don't re-download papers that already exist (check file first)

- If auto-action fails (git clone timeout, package not found), log the failure but don't retry until next cycle



**Consistent format across all pipelines:**

```

[0.85] [TIER 1] Finding headline — why it matters

[0.55] [TIER 2] Another finding

```



**Calibrating thresholds by source:** Categories with natural name-bonus keywords (e.g., Trump-related monitoring where the name alone adds +0.25) will score higher across the board. Business intelligence categories without celebrity names naturally cluster 0.25-0.60. Set alert thresholds per category group rather than globally:

- Trump/KB categories: TIER 1 at 0.75+, TIER 2 at 0.50-0.74

- Business intel categories: TIER 1 at 0.55+, TIER 2 at 0.30-0.54

- AI/ML research: TIER 1 at 0.70+, TIER 2 at 0.40-0.69 (LLM-assigned, not keyword-based)



See `references/boss-radar-scoring.md` for the full rubric and implementation examples.



### Phase 9: Focus Recommendation + Quick Wins + ADHD Check



**Focus Recommendation (required every pulse):**

- Always recommend ONE specific, actionable thing — not 'work on Bookends' but 'deploy the Bookends nginx config and test it'

- Reference the priority list: if P0 is cold and P1 is active, flag it

- If multiple P0 items are stale, pick the one closest to done



**Quick Wins (< 15 min tasks):**

- Generate and send a BizDev outreach email

- Check if yesterday's fixes are deployed

- Review a deprecation notice or release changelog

- Run a smoke test on a deployed service

- These should be low-execution-friction tasks that build momentum



**ADHD Check (concrete heuristics, not abstract):**



Apply these heuristics in order:



1. **Count distinct projects touched in last 24h** — session_search and git log. If >3 AND none are P0, flag it explicitly.

2. **Check for blocked work that consumed time** — if the operator built 2 agent teams today but both need Discord bot tokens (which only he can create manually), that's time spent on blocked work. Flag: "You built [X] but it's dead in the water without [Y manual step]."

3. **Look for the infra-escape-velocity trap** — building infrastructure (MCP servers, agent teams, tooling) instead of shipping products. These feel productive but don't generate cash. "You spent today building [teams/infra/tools] — none of which are P0."

4. **Everything-in-progress-nothing-done pattern** — count active projects with recent commits but no shipping milestone reached. If >=4, the operator is spreading too thin.

5. **Look for the stall-just-before-shipping pattern** — Bookends had commits May 26 then stopped. Construct Manage had a big fix May 28 then stopped. Both were close to done. Flag the gap: "[Project X] was [N] days from shipping and went cold."

6. **P0 cold but P1/P2 hot** — if 2+ P1/P2 items have recent activity while P0 is stale, call it: "You're avoiding [P0 item]. The reason is usually [perfectionism / blocked on a small thing / lost interest]. Let's resolve the blocker."

7. **User absence streak (UTILITY heuristic)** — If no user session found in 4+ days AND all git activity is from subagents/cron, flag: "No user activity in [N] days. All recent commits are from subagents — you haven't logged in since [date]. Everything's running on autopilot." This often indicates burnout or external life factors, not project abandonment. Response: recommend the smallest possible re-engagement task (5 min, one commit, one email, one decision) rather than a full feature push.



8. **Pre-migration freeze pattern** — When multiple repos share the exact same last-commit date AND commit messages contain "pre-migration" or "prep:", the user hit a migration wall and abandoned everything at once. This differs from stall-just-before-shipping (heuristic 5) in two ways:

   - **Root cause:** Migration friction (broken builds, config conflicts, docs to update), not perfectionism/fear of launch

   - **Scope:** Affects 3+ repos simultaneously, not one at a time

   - **Pulse response:** Don't tell them to "just ship" — the blocker is unfinished migration work. Ask specific questions: "Did the migration complete? Did something break? Can I test the migration on ONE repo to find the friction point?" If the migration genuinely stalled, recommend officially parking those repos rather than leaving them in ambiguous pre-migration limbo. Clean closure (a commit message saying "parked — migration deferred") is better than silence.

   - **Detection via cross-repo same-date check** (Phase 6 subsection): runs the awk one-liner over all repos, flags any date with 3+ repos. If the commit messages are "pre-migration commit" or "prep:", escalate to pulse headline.



**Recommendation format:** Always give ONE specific actionable thing — not 'work on Bookends' but 'deploy the Bookends nginx config and push to prod'. The more specific the next step, the more likely the operator executes it.



**Escalation on repeated findings (NEW v1.18.0):** If the same critical finding appears in 3+ consecutive pulses (e.g., "BizDev 0 outreach" unchanged, "P0 cold" repeated), **escalate the framing** rather than repeating the same warning. Options in escalation order:

1. **Shift from descriptive to direct:** "This is the 4th straight pulse with 0 BizDev outreach. That's not a stall — it's a choice not to act. What's the actual blocker?"

2. **Call the pattern by name:** "You're in a P0-avoidance loop. The evidence: [list repeated findings]. The root cause is usually [perfectionism / blocked on small thing / lost interest]. Pick ONE 5-minute action."

3. **Change the ask size:** Instead of a session-long task, recommend a 2-minute action. "Open one LinkedIn message template. Don't send it. Just open it and read it. That's the task." Micro-commitments break avoidance loops.

4. **Offer to do it for them:** If the blocker is a scriptable action (drafting, data prep, config), say so explicitly.



Do NOT let a pulse with 3+ identical consecutive findings end with the same recommendation format as pulse #1. The user will start skimming.

