# Open Coscientist SSE Transport Discovery

**Date:** 2026-07-30  
**Server:** `open-coscientist-lit-review` v2.14.7  
**Port:** 8888  
**Transport:** SSE (not StreamableHTTP)  
**Tools:** 11 biomedical research tools

## Background

Open Coscientist (`open-coscientist-lit-review` v2.14.7) runs as a Docker container and exposes an MCP endpoint on port 8888. It was originally thought to use StreamableHTTP transport (since the config URL is `http://localhost:8888/mcp`), but investigation revealed it uses the original SSE transport.

## Discovery Process

### Step 1: Basic connectivity check

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  http://localhost:8888/mcp
# → 200
```

### Step 2: Add `-v` to check response headers

```bash
curl -v -s \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  http://localhost:8888/mcp 2>&1 | tail -20
```

Key observation:
```
< content-type: text/event-stream
< x-accel-buffering: no
< Transfer-Encoding: chunked
...
event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}
```

**`content-type: text/event-stream`** confirmed SSE transport. The server runs on **uvicorn**.

### Step 3: Attempting tools/list with plain JSON pipe → FAILS

```bash
curl -s ... -d '{"jsonrpc":"2.0","method":"tools/list",...}' \
  http://localhost:8888/mcp | python -c "import json; ..."
# → json.decoder.JSONDecodeError: Expecting value
```

The raw SSE response includes `event: message` and `data:` lines that aren't valid JSON.

### Step 4: Using SSE extractor pattern → WORKS

```bash
response=$(curl -s ... http://localhost:8888/mcp)
echo "$response" | grep "^data: " | sed 's/^data: //' | python -c "import json, sys; ..."
# → Tools count: 11
```

### Step 5: Verified all 11 tools operational

```
check_pubmed_available → true
search_pubmed(query, max_papers) → real 2026 papers
pubmed_search_with_fulltext(query, slug, max_papers, recency_years)
query_gene_disease_network(ids)
query_gene_codependents(ids)
query_drug_info(ids)
query_clinical_trials(ids)
query_pathways(gene_ids)
query_causal_subnetwork(...)
query_mechanistic_statements(...)
run_enrichment_analysis(gene_list)
```

## Key Takeaways

1. **MCP servers configured with `url:` do NOT guarantee StreamableHTTP.** Always check `content-type` in response headers.
2. **SSE ↔ StreamableHTTP confusion** is the single most common transport mis-identification. The fix is always `curl -v` on the initialize call.
3. **Open Coscientist is a hybrid**: it accepts POST requests directly on `/mcp` but returns SSE responses, unlike pure SSE servers that require a separate GET endpoint + session_id routing.
4. **Wilson's `x-accel-buffering: no` header** paired with `Transfer-Encoding: chunked` is a strong signal of an SSE server behind a proxy.
5. **The grep+sed extractor works universally** for SSE-based MCP servers regardless of the specific SSE framing format.

## Tools That Use This Pattern

- `open-coscientist-lit-review` on port 8888 (confirmed)
- Any uvicorn-based MCP server with SSE transport
- Servers wrapping `fastmcp.FastMCP(transport="sse")` or raw `mcp.server.Server` with SSE app
