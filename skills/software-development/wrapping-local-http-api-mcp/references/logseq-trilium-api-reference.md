# Logseq + Trilium API References

Concise field notes for wrapping these two apps as MCP servers. Both follow the same pattern: stdio MCP server bridges Hermes to the app's built-in HTTP API.

## Logseq

**Setup:** Logseq desktop → Settings → Developer → Enable HTTP APIs server + set Auth token.
**Config.edn keys:** `:server/tokens ["token"]` and `:server/autostart true` (not `:http-api-token`).
**Endpoint:** `POST http://localhost:12315/api`
**Auth:** `Authorization: Bearer <token>`
**Format:** JSON-RPC with `method` + `args[]` positional arguments.

**Versions note:** Logseq 0.10.x portable may not support the HTTP API even with config.edn
settings. The API requires enabling in the Settings UI, and old versions lack the server code.
If the HTTP API isn't available, fall back to reading/writing Logseq's markdown files directly
(Logseq stores pages as `.md` files in `<graph>/pages/`).

| Tool Name | Logseq Method | Args |
|-----------|--------------|------|
| `logseq_health_check` | `logseq.App.getCurrentGraph` | `[]` |
| `logseq_create_page` | `logseq.Editor.createPage` | `[name, props?, opts?]` |
| `logseq_get_page` | `logseq.Editor.getPage` | `[name]` |
| `logseq_get_page_blocks_tree` | `logseq.Editor.getPageBlocksTree` | `[name]` |
| `logseq_create_block` | `logseq.Editor.insertBlock` | `[parentUuid, content, opts?]` |
| `logseq_append_block_to_page` | `logseq.Editor.appendBlockInPage` | `[page, content]` |
| `logseq_update_block` | `logseq.Editor.updateBlock` | `[uuid, content]` |
| `logseq_get_block` | `logseq.Editor.getBlock` | `[uuid]` |
| `logseq_remove_block` | `logseq.Editor.removeBlock` | `[uuid]` |
| `logseq_get_all_pages` | `logseq.Editor.getAllPages` | `[]` |
| `logseq_datalog_query` | `logseq.DB.q` | `[datalogQuery]` |

**Datalog search example:**
```
[:find (pull ?b [:block/content :block/page]) :where [?b :block/content ?c] [(clojure.string/includes? ?c "search term")]]
```

**createPage opts:** `{"createFirstBlock": true, "journal": false}`
**insertBlock opts:** `{"sibling": false, "before": false}`

**Config:**
```yaml
mcp_servers:
  logseq:
    command: python
    args: ["<scripts>/mcp_logseq_server.py"]
    env:
      LOGSEQ_TOKEN: ${LOGSEQ_TOKEN}
      LOGSEQ_URL: http://localhost:12315/api
    timeout: 30
```

## Trilium Notes

**Setup:** Running Trilium instance (Docker or desktop server mode). For headless Docker setups,
initialize with `POST /api/setup/new-document` then inject ETAPI token directly into SQLite.
**Base:** `http://localhost:<port>/etapi` (default 8080, but Docker Desktop often uses 8090)
**Auth:** `Authorization: <token>` (bare or `Bearer <token>`)
**Format:** Standard REST, JSON bodies. Note content is raw text/html on PUT.

**Token hash encoding (CRITICAL):** Trilium stores SHA-256 hashes in **base64** encoding,
NOT hex. When injecting tokens into SQLite:
```javascript
const hash = crypto.createHash("sha256").update(raw).digest("base64");  // ✓
// NOT: crypto.createHash("sha256").update(raw).digest("hex");           // ✗
```
If auth silently returns 401, the hash encoding is the most likely cause.

**Correct API paths (verified against Trilium v0.104.1):**

| Tool Name | HTTP Method + Endpoint | Notes |
|-----------|----------------------|-------|
| `trilium_health_check` | `GET /app-info` | Works with bare token or Bearer |
| `trilium_create_note` | `POST /create-note` | NOT `POST /notes` (that returns 404) |
| `trilium_get_note` | `GET /notes/{id}` | Full metadata + child/parent IDs |
| `trilium_get_note_content` | `GET /notes/{id}/content` | Returns raw HTML/text |
| `trilium_update_note_content` | `PUT /notes/{id}/content` | Body is raw text/html, not JSON |
| `trilium_update_note_metadata` | `PATCH /notes/{id}` | `{title?, type?, mime?}` |
| `trilium_delete_note` | `DELETE /notes/{id}` | |
| `trilium_search_notes` | `GET /notes?search={query}` | NOT `POST /search/search` |
| `trilium_get_note_tree` | `GET /notes?limit=500` | ETAPI has no `/tree` endpoint |
| `trilium_create_branch` | `POST /branches` | `{parentNoteId, childNoteId, prefix?, notePosition?}` |
| `trilium_list_recent_notes` | `GET /notes/history` | NOT `GET /recent-notes` |
| `trilium_create_relation` | `POST /notes/{id}/relations` | `{relationName, targetNoteId}` |
| `trilium_get_inbox` | `GET /inbox/{date}` | Date required |
| `trilium_list_attributes` | `GET /attributes` | |

**Note types:** `text`, `code`, `file`, `image`, `search`, `book`, `relationMap`, `render`

**Config:**
```yaml
mcp_servers:
  trilium:
    command: python
    args: ["<scripts>/mcp_trilium_server.py"]
    env:
      TRILIUM_TOKEN: ${TRILIUM_TOKEN}
      TRILIUM_URL: http://localhost:8080
    timeout: 30
```

**Docker setup (headless):**
1. `docker run -d --name trilium -p 8090:8080 -v trilium-data:/home/node/trilium-data triliumnext/trilium`
2. `curl -X POST http://localhost:8090/api/setup/new-document -H "Content-Type: application/json" -d '{"password":"...","passwordVerification":"..."}'`
3. Inject ETAPI token: use node inside container to generate SHA-256 base64 hash
4. Verify: `curl -s http://localhost:8090/etapi/app-info -H "Authorization: <token>"`

## Design Decisions Made in the Implementations

1. **Raw mcp SDK, not fastmcp** — fastmcp 3.4.x has protocol handshake bugs (`Received request before initialization was complete`). The raw `mcp.server.Server` + `@server.list_tools()` decorators work reliably.
2. **12+14 tools** — Logseq exposes 12 (pages, blocks, Datalog), Trilium exposes 14 (CRUD, tree, search, relations, attributes). Both cover full read/write.
3. **Graceful degradation** — Both servers return `CallToolResult(isError=True)` with a message like "Cannot reach Logseq at ..." instead of crashing if the app isn't running.
4. **Absolute paths** — MCP server args in config.yaml must be absolute paths since Hermes spawns subprocesses without setting a working directory. Use forward slashes on Windows to avoid YAML escape issues.
