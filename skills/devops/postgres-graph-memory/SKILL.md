---
name: postgres-graph-memory
description: "Use when building Postgres graph/GraphRAG memory (pgGraph)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [postgres, graph, pggraph, polygres, graphrag, memory, mcp, agent-memory, entities, graph-extension]
    triggers: [pggraph, polygres, graph-database, graphrag, graph-memory, postgres-graph, entity-graph, graph-extension, unlimited-context, context-window]
    related_skills: [infrastructure-technology-evaluation, vector-databases, local-supabase, mcp-server-onboarding]
---

# Postgres Graph Memory (pgGraph / Polygres)

Add graph traversal + GraphRAG to plain Postgres so agents answer multi-hop questions
(people ↔ orgs ↔ properties ↔ emails ↔ signals) without dumping whole tables into context.
This is the **relational memory layer** of a layered agent-memory architecture:

```
compression (Headroom/Context Mode) → relational graph (this) → code graph (codebase-memory-mcp) → agent memory (agentmemory) → narrative KB (MemPalace)
```

Clarify up front when the user says "unlimited context": a graph store gives the *illusion* of
infinite context via bounded retrieval — it is NOT a bigger model token window.

## Verified stack (2026-08-01, `ghcr.io/evokoa/pggraph:1.0.0`)

- Image ships **Postgres 17 + `graph` extension 1.0.0** (`CREATE EXTENSION graph` works).
- Container: `hermes-pggraph`, host port **5435** (avoid Supabase 54322 / agency stack 5432).
- Committed reference implementation lives in `pmb2/hermes-config`:
  - `infra/pggraph/` — docker-compose.yml, `.env`, `sql/01_schema.sql` (entities.* schema),
    `sql/02_seed.sql` (land/builder sample graph), `sql/04_register_pggraph.sql`, `up.sh/down.sh/psql.sh`
  - `scripts/pggraph-mcp/server.py` — FastMCP server + CLI test fallback
  - `config/memory/mcp-pggraph.snippet.yaml` — Hermes MCP wiring snippet
  - `docs/guides/PGGRAPH_INTEGRATION.md` — full guide

## Setup

```bash
# 1. Compose (init SQL auto-runs ONLY on first volume boot)
docker compose -f infra/pggraph/docker-compose.yml up -d
docker exec hermes-pggraph pg_isready -U hermes -d hermes_graph   # wait for READY

# 2. Re-apply schema manually after first boot (initdb does not re-run):
docker exec -i hermes-pggraph psql -U hermes -d hermes_graph < sql/01_schema.sql
docker exec -i hermes-pggraph psql -U hermes -d hermes_graph < sql/02_seed.sql
docker exec -i hermes-pggraph psql -U hermes -d hermes_graph < sql/04_register_pggraph.sql
```

DSN: `postgresql://hermes:hermes_graph_dev@localhost:5435/hermes_graph` (change creds in `.env` for prod).

## pgGraph v1.0.0 API (verified signatures)

```sql
CREATE EXTENSION graph;

-- Register a source table. REAL signature (probe first with
-- SELECT pg_get_function_identity_arguments(oid) FROM pg_proc
-- WHERE proname='add_table' AND pronamespace='graph'::regnamespace):
SELECT graph.add_table('entities.people'::regclass, 'id', ARRAY['name','email'], NULL);

-- Build the persisted CSR artifact: (nodes, edges, mb, secs, sync_mode, projection)
SELECT graph.build();
-- WARNING if no tables registered: "no tables registered. Call graph.add_table() first."

-- Source-row search (returns verified coordinates + optional hydrated JSONB)
SELECT * FROM graph.search(property_key:='name', property_value:='Lennar',
  table_filter:='entities.orgs'::regclass, mode:='contains',
  case_sensitive:=false, max_rows:=10);
```

`graph.auto_discover()` exists but discovers **0 tables** for app schemas — register explicitly.
`graph.gql()` / `graph.cypher()` are documented subsets; start with SQL wrappers.

## MCP tools pattern (bounded queries only)

| Tool | Purpose |
|------|---------|
| `graph_health` | connectivity + extension versions + node/edge counts |
| `graph_search` | text search across registered entity tables |
| `graph_neighbors` | 1..N hop expansion over `entities.edges` (cap depth ≤ 4, limit ≤ 100) |
| `graph_path` | BFS shortest path between two `(table, uuid)` nodes |
| `graph_subgraph` | neighborhood + hydrated labels for prompt context |

Server: `mcp[FastMCP]` with a CLI fallback (`python server.py graph_health`, `python server.py graph_search '{"query":"Lennar"}'`) for testing without an MCP client.

## Pitfalls

- **`docker exec` without `-i` swallows heredoc stdin.** Use `docker exec -i ... psql <<EOF` or `-c` strings.
- **`graph.add_table` old/alternate shapes fail** — `(regclass)` and `(regclass, jsonb)` are NOT v1.0.0.
  The working form is `(regclass, id_column, columns text[], tenant_column)`.
- **`graph.build()` warns about triggers** when `sync_mode='trigger'`; set `graph.sync_mode='manual'` before build to opt out of auto-sync triggers.
- **Schema init only on first boot** — editing `sql/*.sql` after the volume exists does nothing; re-apply manually.
- **Two-Python box (Windows host):** the `execute_code` sandbox interpreter may lack `psycopg` while terminal `python` has it. Test MCP handlers via terminal `python`, not `execute_code`.
- **Search-only backends can't extract GitHub pages** — use `gh api repos/<owner>/<repo>/readme` + base64 decode for README review instead of web_extract when the extract backend is ddgs.
- **Bounded queries are mandatory** — agents must not dump the whole graph; always cap depth/rows.

## Verification

```bash
docker exec hermes-pggraph psql -U hermes -d hermes_graph \
  -c "SELECT (SELECT count(*) FROM entities.people),(SELECT count(*) FROM entities.edges);"
# expect graph ext listed:
docker exec hermes-pggraph psql -U hermes -d hermes_graph \
  -c "SELECT extname, extversion FROM pg_extension WHERE extname='graph';"
# path demo via MCP:
PGGRAPH_DSN=postgresql://hermes:hermes_graph_dev@localhost:5435/hermes_graph \
  python server.py graph_path '{"src_table":"people","src_id":"<uuid>","dst_table":"orgs","dst_id":"<uuid>","max_depth":5}'
```

## Boundaries / scope

- Not a replacement for MemPalace (narrative KB), Hermes memory (durable facts), or compression tools (Headroom/Context Mode). One concern → one system of record.
- WAL live sync is **reserved** in v1.0.0 — use manual/trigger sync.
- This layer is legitimate context engineering; do not conflate it with jailbreak/uncensor tooling (CONFIG-TOGGLE-style `/godmode` bypasses are refused and out of scope).
