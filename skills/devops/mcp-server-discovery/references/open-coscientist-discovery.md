# Open Coscientist MCP Server Discovery (2026-07-26)

Discovered during a Weaver fleet pulse — this server was running for ~2 days
on port 8888 with no agent aware of it. No previous audit had probed port 8888.

## Discovery Transcript

### Step 1: Port enumeration noted port 8888 in netstat output
PID 23072 = `com.docker.backend.exe` (Docker's port proxy).

### Step 2: docker ps resolved the container
`open-coscientist-mcp-server-1`  `open-coscientist-mcp-server`  `0.0.0.0:8888->8888/tcp`  Up 2 days

### Step 3: MCP initialize confirmed it (SSE-wrapped response)
```json
{"jsonrpc":"2.0","id":1,"result":{
  "protocolVersion":"2024-11-05",
  "capabilities":{"experimental":{},"prompts":{"listChanged":true},
    "resources":{"subscribe":false,"listChanged":true},
    "tools":{"listChanged":true},
    "tasks":{"list":{},"cancel":{},
      "requests":{"tools":{"call":{}},"prompts":{"get":{}},"resources":{"read":{}}}}}},
  "serverInfo":{"name":"open-coscientist-lit-review","version":"2.14.7"}}}
```

### Step 4: tools/list returned 11 tools
1. `check_pubmed_available` — test PubMed connectivity
2. `search_pubmed` — search PubMed
3. `pubmed_search_with_fulltext` — search + download PMC fulltext
4. `query_gene_disease_network` — INDRA KG associations
5. `query_gene_codependents` — DepMap CRISPR codependency
6. `query_drug_info` — drug targets, indications, side effects
7. `query_clinical_trials` — trial data for disease/drug
8. `query_pathways` — biological pathways for genes
9. `query_causal_subnetwork` — causal connections between entities
10. `query_mechanistic_statements` — curated INDRA causal claims
11. `run_enrichment_analysis` — GO/pathway/kinase enrichment

### Differentiators
- INDRA knowledge graph tools (4, 5, 6, 7, 9, 10, 11) are unique — no other
  configured MCP server offers biomedical mechanistic reasoning.
- Task management capabilities suggest long-running research workflows.
- Transport is StreamableHTTP (single POST to `/mcp`), wireable without restart.

### Wire Config
```yaml
mcp_servers:
  open-coscientist:
    url: "http://localhost:8888/mcp"
    timeout: 120
    connect_timeout: 15
```

## Diagnostic Patterns From This Discovery
1. **Low-hanging fruit is port probing** — iterating 3000-8888 with MCP initialize
   would find any HTTP MCP server. Most audits only check config entries.
2. **Docker compose doesn't mean onboarded** — running for 2 days, nobody knew.
3. **No `/health` shortcut** — `/health` on port 8888 returned empty.
4. **SSE event-stream wrapping** — response came as `event: message\ndata: {...}`
   even though the request was a standard POST. Ignore the SSE framing.
