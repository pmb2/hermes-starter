# Gap Analysis → Parallel Build Pattern

From session 2026-05-30: after building the initial 10-team, 64-agent framework, the user asked "what are we missing?" and then "build out all your suggestions." This pattern captures the methodology used to identify, prioritize, and deliver 14+ gap items in a single session.

## The Pattern

### Step 1: Scan Everything

Before identifying gaps, read the full current state:

```bash
find . -type f | wc -l                    # Total file count
find teams/*/ -maxdepth 2 -name "AGENTS.md" | wc -l  # Agent count
ls -d teams/*/                             # Existing teams
```

### Step 2: Identify Gaps across Three Tiers

Organize gaps into tiers by severity:

| Tier | Type | Examples |
|------|------|----------|
| **Tier 1** | Missing agents | Health monitor, content factory, market intel, media pipeline |
| **Tier 2** | Operational infrastructure | Comms protocol, emergency procedures, disaster recovery, compartmentalization, onboarding |
| **Tier 3** | Documentation | Quick-start guide, MCP API reference, dependency map, migration guide |

### Step 3: Prioritize

Sort by impact and dependency order:
1. Health monitor first (keeps everything else running)
2. Operational docs second (teams can't coordinate without protocols)
3. Agents third (need protocols to know how to request resources)
4. Guides last (useful but non-blocking)

### Step 4: Build in Parallel Waves

Launch 3-4 concurrent `delegate_task(role='orchestrator')` calls, each handling one category:

- **Wave A — New agents** (3 agents in parallel)
- **Wave B — Operational documents** (5 docs in parallel)  
- **Wave C — Documentation infrastructure** (5 docs in parallel)
- **Wave D — Knowledge tooling** (5 systems in parallel)

Each wave is independent — no file overlap between waves.

### Step 5: Verify Everything

After all 4 waves complete:
- `find teams/*/ -maxdepth 2 -name "AGENTS.md" | wc -l` — count new agents
- Verify each new file exists
- Update AGENT_UNIVERSE.md master index with new agent counts
- Update orchestrator dependency count

## Results from This Session

| Category | Items Built | Files |
|----------|-------------|-------|
| New agents | Health Monitor, Content Factory, Market Intel, Canary, Media Pipeline | 25 |
| Operational docs | Cross-team comms, emergency, disaster recovery, compartmentalization, onboarding | 5 |
| Documentation | Quick-start, MCP API ref, dependency map, migration guide, CI workflow, workstation guide | 6 |
| Knowledge systems | Knowledge Manager, Cost Tracking | 10 |
| **Total** | **16 gap items** | **46 new files** |
