# Diagnosing MCP Server Projects

A systematic methodology for assessing an existing MCP server project's health,
completeness, and readiness — used when someone asks about getting an MCP server
connected to Hermes.

## Assessment Pipeline

### 1. Locate the Project

Check these sources in order:

- **`.mcp.json`** (user home or project root) — MCP servers configured for Claude Code
- **`~/.hermes/config.yaml`** — Hermes-native MCP server configs
- **OpenCode's config** — `opencode.json` may have its own MCP server entries
- **Filesystem search** — look in common project directories (`~/Projects/`,
  `~/Documents/github/`, `~/Code/`)

Look for the `workingDirectory` / `cwd` / `args` fields to find the actual project path.

### 2. Snapshot the Project Structure

```python
# Quick scan
ls -la <project_root>/                    # Top-level layout
find <project_root> -type f -name "*.py" -o -name "*.md" -o -name "*.toml" \
  -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" | head -50
```

Key files to examine:
- `README.md` — features, setup instructions, tool list
- `pyproject.toml` / `package.json` / `Cargo.toml` — dependencies, entry point
- `app/main.py` or `src/index.ts` — entry point, tool definitions
- `.env` / `.env.example` — required env vars
- `app/config.py` — settings schema (pydantic-settings, env var names)
- `tests/` — test coverage breadth
- `migrations/` — database schema management
- Dockerfile / docker-compose.yml — container setup

### 3. Dependency Audit

Check whether required packages are installed and compatible:

```sh
# Python
cd <project_root> && python -c "import <package>; print(<package>.__version__)"

# Check pyproject.toml for version pins vs. installed versions
grep -A20 '\[project\]' pyproject.toml
```

**Common version conflicts:**
- `fastmcp` + `pydantic` version incompatibility (fastmcp 2.x requires pydantic 2.14+;
  fastmcp 0.4.1 works with pydantic ~2.10; fastmcp 1.0 has protocol init bugs with mcp 1.27+)
- `pydantic-settings` and `pydantic` minor version skew (pydantic-settings 2.6 works with pydantic ~2.10;
  pydantic-settings 2.14 requires pydantic 2.13+)
- `aiosqlite` version mismatch (>=0.20 required by some async SQLite usage patterns)
- `mcp` SDK version vs `fastmcp` version compatibility (fastmcp 0.4.1 works with mcp ~1.1;
  fastmcp 1.0 has issues with mcp 1.27; fastmcp 2.x requires mcp ~2.x)

Fix with pinned installs: `pip install "fastmcp>=0.4,<1.0" "mcp>=1.0,<1.2" "pydantic>=2.10,<2.14"`

### 4. Startup Test

Start the server in background and verify it stays running:

```python
# Background start
terminal(command="cd <project> && python -m app.main", background=True)

# Poll for status (after 2-3 seconds)
process(action="poll", session_id="...")
```

**Critical: kill background instances before re-testing.** An MCP server holds
the SQLite database lock while running. If you spawn a second test instance
(via Python subprocess or another terminal call), it will hang or deadlock
waiting for the first instance to release the lock. Always do:

```
process(action="kill", session_id="<previous_session>")
```

before spawning a fresh test.

**Testing via the MCP client library (preferred):**

Use the `mcp` Python client library rather than raw JSON-RPC over stdin/stdout.
The library handles the initialization handshake (`initialize` → `notifications/initialized`),
request/response framing, and error serialization automatically:

```python
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession

async def test():
    params = StdioServerParameters(
        command="python", args=["-m", "app.main"]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            tools = await session.list_tools()
            print(f"{len(tools.tools)} tools registered")
            result = await session.call_tool("health_check", {})
            print(result.content)
```

**Avoid raw JSON-RPC testing.** Sending raw JSON-RPC messages to stdio is
fragile — the `mcp` SDK validates message schemas strictly and rejects
manually-crafted messages that don't match its typed request union. Use
`ClientSession.list_tools()`, `.call_tool()`, etc. instead.

**Check stderr separately** (stdout is consumed by MCP protocol):

```sh
python -m app.main 2>/tmp/mcp_stderr.log
cat /tmp/mcp_stderr.log
```

Common startup failures:
- **ModuleNotFoundError** — missing dependency (install from pyproject.toml)
- **ImportError at module level** — code tries to connect to DB / API on import
- **Pydantic validation error** — env var type mismatch
- **Port conflict** — HTTP transport server already bound
- **"no such table" / empty DB** — server ran from wrong working directory (see §8)

### 5. Architecture Analysis

**Detect competing architectures** — the biggest red flag in a half-built project:

| Signal | What It Means |
|--------|---------------|
| Multiple `db.py` or model files with different schemas | Two design phases stacked, not reconciled |
| `app/tools/` files import ORM models that don't exist | Advanced tooling was planned before the model layer was built |
| `app/ingestion/` uses different DB approaches than `main.py` | Ingestion pipeline and server diverged |
| Pydantic schemas in `models/` but no SQLAlchemy ORM classes | Schema-first design that never got ORM wiring |
| Embedding / AI files stubbed with `return None` | Feature planned, placeholder, not implemented |

**The dual-architecture pattern:**
- Phase 1 (working): Raw SQL/aiosqlite in `main.py`, minimal tables
- Phase 2 (half-built): ORM models + advanced tools + ingestion pipeline — all interdependent, none fully wired

Fix: Add the missing SQLAlchemy ORM models to `app/db.py`, then the tools/ingestion pipeline works.

### 6. Database State Check

```python
import sqlite3
conn = sqlite3.connect('<path>/<db>.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
for t in cur.fetchall():
    cur.execute(f'SELECT COUNT(*) FROM "{t[0]}"')
    count = cur.fetchone()[0]
    print(f'{t[0]}: {count} rows')
conn.close()
```

Check whether the DB was populated by a prior ingestion run vs. being empty.

### 7. Completion Estimation

| Category | 100% Indicators |
|----------|-----------------|
| **Core server** | Starts without errors, responds to MCP `tools/list`, tools work end-to-end |
| **Dependencies** | `pip install` completes without conflicts |
| **Database** | Schema matches code, data populated, tools query correctly |
| **Tool coverage** | All promised tools in README are wired as `@mcp.tool()` in main.py |
| **Advanced features** | Search, recommend, classify, score — all callable without ImportError |
| **Ingestion pipeline** | Full fetch → classify → score → embed chain runs without errors |
| **Tests** | `pytest` passes, covers core functionality |
| **Config** | `.mcp.json` entry exists, env vars documented, Hermes `config.yaml` entry ready |

Use the ratio: `(working features count / total features count) × 100` as the baseline,
then subtract penalties for broken imports, missing deps, and competing architectures.

## Common Issues Found

### Missing ORM Models Behind Advanced Tools

The tool files (`search.py`, `recommend.py`, `compare.py`, etc.) import ORM model
classes (e.g., `from app.db import GitHubRepo`), but `app/db.py` only has raw SQL
helpers — no SQLAlchemy `declarative_base()` models.

**Fix:** Add to `app/db.py`:

```python
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class GitHubRepo(Base):
    __tablename__ = "github_repos"
    id = Column(String, primary_key=True)
    full_name = Column(String, unique=True, nullable=False)
    # ... all columns matching the schema
```

**Also needed:** an async engine + session factory so the ORM tools can use
`AsyncSession`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

ASYNC_DB_URL = "sqlite+aiosqlite:///./gitmcp.db"
async_engine = create_async_engine(ASYNC_DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
```

### Mixed Database URLs

The `.env` / `config.py` may use `sqlite+aiosqlite:///` while a secondary ingestion
script hardcodes a postgres URL. Unify to the same database.

### Embedding Placeholders

Embedding modules may be stubbed (`return None`). For v1 this is acceptable if
you don't need vector search — just note it as a gap.

### SQLite Database not Found (Wrong Working Directory)

If the server uses a local SQLite DB (`./mydb.db`) and fails at runtime with
"no such table" or the DB is empty, the server likely ran from the wrong
directory. MCP servers spawned by Hermes inherit the agent's working directory,
not the project directory.

**Fix:** Add an `os.chdir` to the server's entry point so it always runs from
its own project root:

```python
# At the top of main.py, before any DB access:
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
```

This is a lightweight alternative to requiring `workingDirectory` config (which
Hermes does not support for MCP servers).

### Missing Database Columns (Schema Migration)

When adding ORM models to match an existing SQLite database, the table may be
missing columns that the code expects (common in dual-architecture builds where
Phase 1 raw SQL tables were minimal and Phase 2 code was written against a
richer schema).

**Detection:** Compare `PRAGMA table_info(tablename)` output against your ORM
model's column list.

**Fix:** Add missing columns with ALTER TABLE:

```python
cursor = await db.execute("PRAGMA table_info(table_name)")
existing = {row[1] for row in await cursor.fetchall()}
missing = {"new_col": "INTEGER DEFAULT 0", ...}
for col_name, col_type in missing.items():
    if col_name not in existing:
        await db.execute(f"ALTER TABLE table_name ADD COLUMN {col_name} {col_type}")
```

Keep this migration in `init_db()` so it runs on every startup — it's idempotent.

### IngestionRun Type Coercion

When an `IngestionRun` ORM model has `errors: Mapped[str]` (Text column storing
JSON) but the ingestion code assigns Python lists, override `__init__` and
`__setattr__` to auto-serialize:

```python
class IngestionRun(Base):
    __tablename__ = "github_repo_ingestion_runs"
    errors: Mapped[str] = mapped_column(Text, default="[]")

    def __init__(self, **kwargs):
        if "errors" in kwargs and not isinstance(kwargs["errors"], str):
            kwargs["errors"] = json.dumps(kwargs["errors"])
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        if name == "errors" and not isinstance(value, str):
            value = json.dumps(value)
        super().__setattr__(name, value)
```

Same pattern applies to `id` fields that receive `uuid.UUID` objects — convert
to `str()` in `__init__`.

### SQLite List-Type Fields (JsonList TypeDecorator)

When a SQLAlchemy ORM model has fields that store Python lists (like `topics`,
`agent_fit`, `input_types`, `output_types`), direct assignment of a list
to a `Text` column fails with:

```
sqlite3.ProgrammingError: Error binding parameter N: type 'list' is not supported
```

**Fix:** Create a SQLAlchemy `TypeDecorator` that auto-serializes/deserializes
lists as JSON:

```python
from sqlalchemy import TypeDecorator, Text

class JsonList(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
```

Then use it in your model:

```python
class GitHubRepo(Base):
    __tablename__ = "github_repos"
    topics: Mapped[Optional[list]] = mapped_column(JsonList, nullable=True)
```

This makes list-to-JSON serialization transparent — code assigns `repo.topics = ["ai", "agents"]`
and reads back `["ai", "agents"]` without manual `json.dumps`/`json.loads`.

**Note:** SQLite's `JSON` column type is parsed as text, not a native JSON array.
`TypeDecorator` with `impl=Text` is the portable solution that works across
SQLite, PostgreSQL, and MySQL. For production PostgreSQL, use SQLAlchemy's
built-in `ARRAY(String)` type instead.

### MCP Server Registration in Hermes Config

Hermes reads MCP servers from `mcp_servers` in `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  git-stars:
    command: python
    args: [-m, app.main]
    env:
      GITHUB_TOKEN: "your_token"
      DATABASE_URL: "sqlite+aiosqlite:///./gitmcp.db"
    timeout: 300
```

**Note:** `workdir` / `cwd` / `workingDirectory` are NOT supported in Hermes
MCP server config (despite being present in `.mcp.json` for Claude Code).
Use the `os.chdir()` pattern in §8 instead.

Servers are discovered on startup only — no hot-reload. Restart Hermes after
adding or changing an MCP server entry.

## Example: GIT-STARS Assessment

See the project at `${MY_REPOS}\Documents\github\git-mcp\services\github-star-intelligence-mcp`
for a real-world example that exhibited all of these patterns:
- Dual architecture (raw SQL in main.py + ORM imports in tools/)
- Missing GitHubManagedRepo model
- Missing capability score columns
- FastMCP/mcp version incompatibility
- Ingestion pipeline with wrong DATABASE_URL
- Working directory mismatch
