# Foreign Codebase Integration Checklist

Use this when integrating an external codebase (e.g., ShadowForge Swarm) into the agent-universe structure.

## Phase 1: Inventory
- [ ] `find . -type f | sort` — full inventory of all files
- [ ] Categorize every file into: Agent code, MCP servers, Skills, Tools, Infrastructure configs, Docs, Misc
- [ ] Note file count by category
- [ ] Read key index/overview docs (README, AGENTS-INDEX, SWARM.md)

## Phase 2: Map
- [ ] Map agent code → new agent directories in appropriate team
- [ ] Map MCP servers → `infrastructure/mcp-servers/src/`
- [ ] Map skills → `shared/skills/src/`
- [ ] Map tools → `shared/tools/src/`
- [ ] Map infra configs → `infrastructure/swarm-configs/` or `infrastructure/deploy/`
- [ ] Map reference docs → appropriate `docs/` dirs
- [ ] Map design docs → team `docs/` dirs

## Phase 3: Create Agent Dirs
- [ ] `mkdir -p teams/NN-team/{agent-name}/{config,tooling,templates,docs,tests}`
- [ ] Create `AGENTS.md` with YAML frontmatter + role
- [ ] Create `README.md` — overview, prerequisites, quick start
- [ ] Create `config/config.yaml`
- [ ] Create `.env.example`
- [ ] Copy source .py files into `tooling/` preserving subdirectory structure
- [ ] Create `docs/integration-map.md` documenting source-to-destination mapping

## Phase 4: Shared Component Dirs
- [ ] `infrastructure/mcp-servers/` — all MCP server .py files + docs + INDEX.md + hermes-config.yaml
- [ ] `shared/skills/` — all skill .py files + docs + INDEX.md
- [ ] `shared/tools/` — all tool .py files + docs + INDEX.md
- [ ] Infrastructure configs merged into `infrastructure/`

## Phase 5: Update Indices
- [ ] Update `TEAM.md` — add new agents to the agent table
- [ ] Update `AGENT_UNIVERSE.md`:
  - [ ] Bump header count: `**XX specialist agents · NN teams · one monorepo**`
  - [ ] Update summary table (agent counts + descriptions)
  - [ ] Add per-team agent tables
  - [ ] Add shared components section if new
- [ ] Update `orchestrator/AGENTS.md` dependency count: `"All XX specialist agents"`
- [ ] Update source directory README to mark as integrated

## Phase 6: Verify
- [ ] Count AGENTS.md files: `find teams/*/ -maxdepth 2 -name "AGENTS.md" | wc -l`
- [ ] Verify header count matches actual agent count (+1 for orchestrator)
- [ ] Verify every team has a TEAM.md
- [ ] Verify all new agents show in `AGENT_UNIVERSE.md` table
- [ ] Verify agent subdirectories are at correct depth (not under `agents/`)
- [ ] Verify no `__pycache__` or `.pyc` files were included

## Pitfalls
- New agents created by sub-agents may be nested under `agents/` instead of directly under the team dir — check and move them up
- AGENT_UNIVERSE.md table rows need single leading `|` — no triple pipes
- Always bump BOTH the total count AND per-team count in AGENT_UNIVERSE.md
- Preserve original source files — copy, don't move
- Check `__init__.py` files for broken imports (files may reference modules that don't exist in the source)
