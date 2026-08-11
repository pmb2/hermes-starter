---
name: idea-to-product
description: >-
  Full pipeline from a raw product idea (voice memo, free-form conversation,
  or one-line pitch) to a working, tested, documented codebase on GitHub.
  Covers PRD synthesis → architecture design → scaffold → tests → docs →
  AGENTS.md → git → repo + issue.
version: 1.0.0
metadata:
  hermes:
    tags: [product, implementation, buildout, greenfield, workflow]
    triggers:
      - I want to build out this app
      - build this idea
      - turn this into a product
      - I want to build an app that
      - greenfield project from scratch
      - build out the whole thing
    related_skills:
      - to-prd
      - complete-implementation-cycle
      - github
      - agents-md-hierarchy
      - test-driven-development
      - writing-plans
---

# Idea to Product

When the user starts describing a product idea in free-form (voice memo, conversation, one-line pitch) — follow this pipeline to get from idea to a working, tested, documented repo on GitHub.

## Workflow Phases

### Phase 0: Quick content sweep

Before writing anything, search for existing artifacts — prior notes, repos, brainstorms, issues. Avoid building on top of nothing when something already exists. Use `session_search`, `search_files`, and `memory` recall.

### Phase 1: Synthesize the PRD

Use the `to-prd` skill to draft the PRD. Key differences from `to-prd`'s standard flow:

**The PRD for a greenfield product includes harder thinking up front:**
1. **Identify the hard problem early** and call it out explicitly in Implementation Decisions. For Deal Finder it was *item identity* (bank transactions don't carry SKUs). Name the true difficulty — the thing that makes this product non-trivial — and document the resolution strategy with fallback confidence tiers.
2. **Design the module seams at the PRD stage** — not later. List the N modules, what each one owns, and what their interfaces look like, even at the dataclass level. The modules are the architecture. Don't start coding without them.
3. **Identify the crown-jewel engine.** Every product has one module that is the moat — the thing competitors would find hardest to replicate because it encodes a hard constraint or a deep domain insight. For Deal Finder it was the no-interruption decision engine. Name it, protect it, test it exhaustively.
4. **Write the canonical test case.** One scenario that encodes the product's core promise. For Deal Finder: "40 cold brews at 40% off covers 10 weeks of consumption and knocks the item off the shopping list." This test case drives every implementation decision. Write it during the PRD phase even though it goes in the test file later. If the canonical test makes no sense given your architecture, the architecture is wrong.
5. **Include a Trust Posture section** when the product touches sensitive data (finance, personal habits, identity). What does the system promise it will NEVER do? Encode that in the module boundaries (read-only adapters, no auto-purchase code paths, no data sale).

Cover these in the PRD file before the Implementation Decisions section. The PRD stays high-level; the canonical test case is the single code artifact you embed.

### Phase 2: User check-in style

the operator's preference: present the PRD as a tight summary (5-7 bullet points across architecture, key decisions, canonical test, and out-of-scope), then ask ONE question: "Approve to publish?" with the target (repo name + issue #1 + label).

Do NOT ask about individual decisions. The architecture was designed in Phase 1. Present the package. If the user revises, fold the revision into the PRD and re-present. If they say "do that now" or "continue", proceed directly to Phase 3.

### Phase 3: Scaffold the code

**Order of scaffold:**
1. `pyproject.toml` (src layout, test config, optional extras)
2. `models.py` (plain dataclasses shared by all modules — puts the domain model on the table first)
3. **The crown-jewel engine** (the constraint engine — write this module before any adapter, before the storage layer, before the alert formatters. Its tests define the product.)
4. Each domain module in dependency order (profile → pantry → deals → freebie)
5. Adapters (light normalization with injected fetchers)
6. Storage (SQLite DAO, thin)
7. Alert formatters (pure functions)
8. `__init__.py` files for every package

**Pattern for each module:**
- Write the module and its **test file** in the same call. Do not write a module without writing at least the test header and primary test case.
- Modules are pure domain logic. IO lives at the edges (adapters, storage, alerts).
- If a module has a hard rule ("never auto-send", "no-interruption checked first"), test the violation case explicitly — not just the happy path.

```python
# Pattern: test the violation first
def test_late_arrival_never_recommended_no_matter_the_savings():
    verdict = evaluate_deal(ITEM, make_deal(total_price=16.0, delivery_days=11), RUN_OUT, AS_OF)
    assert verdict.kind == VerdictKind.NO_ACTION
    assert "must arrive by" in verdict.reasons[0]
```

### Phase 4: Test-then-fix loop

After ALL modules are written (not after each one — you need the holistic picture to catch interface mismatches):

```bash
python -m pytest
```

If failures: fix each, re-run. Key traps:
- Relative import errors (package root modules use `from .models import`, internal modules use `from ..models import`)
- Signature changes between writing a module and writing the caller
- `dataclass` field ordering

Then lint:

```bash
ruff check .
```

Fix all lint issues. The most common in greenfield: unused imports/variables from iterating module interfaces, and `f`-string without placeholders on continued strings.

### Phase 5: Documentation

Write these in order:

1. **README.md** — one-liner value prop, the loop, architecture table, setup, trust posture, status
2. **AGENTS.md** — DOX-format. Purpose, Ownership (product vision + authority), **Local Contracts** (the binding rules from Phase 1's trust posture + crown-jewel invariants), Work Guidance (language/pattern conventions), Verification, Child DOX Index
3. **`docs/architecture.md`** — from-scratch data flow diagram (ASCII), module descriptions with interface summaries, the canonical test case explained in prose, roadmap
4. **`docs/<feature-module>.md`** — for modules that need dedicated docs (Freebie Finder, or any module with complex rules/guardrails). Hard rules and non-negotiables go here.
5. **`.gitignore`** — at minimum: `__pycache__/`, `*.egg-info/`, `.venv/`, `data/`, `*.db`, `.env`, OS artifacts
6. **Example config** — `configs/example.env` with all credential keys, empty, with signup link comments for each service

### Phase 6a: MCP server layer (after greenfield, for AI-agent consumption)

When the user says "make this consumable by AI agents" or "set it up as MCP server":

The library is already built as pure domain modules. **Wrap it, don't rewrite.**

**Prefer raw `mcp.server.Server` protocol over FastMCP** for toolsets with 5+ tools. This gives full control over tool namespacing, descriptions, and dispatch without the FastMCP abstraction:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("your-service")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="your_service__tool_name", description="...", inputSchema={...}),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Dispatch by name, call pure-domain functions, wrap in TextContent
    ...

async def serve_stdio():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

def cli():
    import anyio
    anyio.run(serve_stdio)
```

**Key pattern:** tool handlers are **thin wrappers** — no business logic in the MCP layer. Domain functions stay independently testable with zero MCP dependency.

**Expansion order:**
1. Add `mcp = ["mcp>=1.0,<2", "anyio>=4.0,<5"]` to `pyproject.toml` optional-dependencies
2. Create `src/<package>/mcp/server.py` with all tool handlers
3. Add `[project.scripts]` entry point: `my-service-mcp = "package.mcp.server:cli"`
4. Create `docs/mcp-server.md` — tool reference, agent integration guide, Hermes `config.yaml` snippet
5. Write import smoke test: `python -c "from pkg.mcp.server import cli; print('OK')"`
6. Run `ruff check --fix` — f-strings without placeholders on continued strings are common in MCP server code

**Tool naming:** Use double-underscore namespace: `deal_finder__find_deals`. Keeps tools identifiable by source in combined tool lists.

### Phase 6b: Expand core modules (second iteration)

When the user adds a new domain (e.g. restaurant promos, gift cards, creative savings):

1. **Start with the data model.** New domain gets its own dataclass file with enums for sources/channels.
2. **Data-driven catalog.** Make catalogs data (list of dataclasses), not code. No code changes for new entries.
3. **Pure normalization.** Parse external formats (APIs, CSV, HTML snippets) into domain types. Adapter pattern with injected fetchers.
4. **Stackable results.** Each module enriches the same output type. Agent queries them independently.
5. **Test normalization, not catalog data.** Write tests for parsing edge cases and transformation logic. Catalog entries are configuration.
6. **Add one MCP tool per module.** Expand the `server.py` dispatch with one new case.
7. **Update docs.** New tool in `docs/mcp-server.md`, new module in `docs/architecture.md`.
8. **Two-layer data-driven filter expansion** (health/purity filter pattern). When the user demands a health/purity/quality gate on products, don't merge it into the existing deal engine. Build a **parallel two-layer system**:
   - **Layer A (universal bans)**: categorical ingredient/compound ban list. Entry = `{keyword, category, risk_level, aliases}`. Substring match against ingredient text. Extend by adding rows.
   - **Layer B (brand intelligence)**: brand→parent→tier mappings. Entry = `{brand, parent, corp_type, health_tier, subsidiaries}`. Subsidiary resolution means a search for a consumer brand ("Cheetos") resolves to its corporate parent ("PepsiCo").
   - **Verdict engine**: combines both layers into a 3-tier output (HEALTHY / FLAGGED / AVOID) with actionable recommendations.
   - **Why separate layers**: ingredient bans are universal (soy is bad regardless of manufacturer); brand health is corporate behavior. Separating gives independent update cadences and prevents one catalog's noise from bloating the other.
   - **Test pattern**: test each layer independently, then test the combined verdict. Write the "brand is BLACK → AVOID" test AND the "brand unknown + clean ingredients → HEALTHY" test.
   - **Add one MCP tool per layer module** — the combined verdict as a single tool is cleaner than separate ingredient and brand tools, but the underlying layers stay independently callable.

### Phase 7: Git + GitHub + Issue

```bash
git init
git add -A
git commit -m "Initial commit: <name> v0.1.0

<3-line summary of the product>
- <list of modules>
- <key architectural point>
- <test count> tests passing
- DOX-style AGENTS.md"
gh repo create <org>/<name> --private --source=. --push
gh label create ready-for-agent --color "0e8a16" --repo <org>/<name>
gh issue create --repo <org>/<name> --label ready-for-agent \
  --title "<Name> — product requirements" --body-file docs/PRD.md
```

## Canonical test case pattern

Every product has one scenario that proves the system does what it says it does. Find it, write it, and anchor every architecture decision to it. Examples:

| Product | Canonical test |
|---|---|
| Deal Finder | "40 cold brews at 40% off covers 10 weeks of consumption and knocks the item off the shopping list. Deal arriving after the run-out deadline is NEVER recommended, regardless of savings percentage." |
| (your next product) | ... |

The canonical test is not a unit test — it's a system-meaning test. It exercises the crown-jewel engine with the most important user scenario. It should be the first test you write and the last test you pass.

## Pitfalls

- **Don't ask permission for architectural decisions.** The user said "build this idea" — not "design this with me." Make the call on language (Python 3.11+), layout (src/), tools (SQLite, FastAPI, pytest), and present the complete package. If the user disagrees about something fundamental they'll say so.
- **Don't write the PRD and stop.** The user's real ask is the product, not the document. The PRD is the first step, not the deliverable.
- **Don't pause after the PRD to ask "should I start coding now?"** The user said "do that now" or "continue" — keep going through the full pipeline until you have a pushed repo with passing tests.
- **The crown-jewel engine's tests are the most important tests in the project.** Write them before the implementation, and write the NO_ACTION cases (violations of the core rule) before the happy path. A decision engine that only tests happy-path recommendations is not tested.
- **Don't hardcode paths or credentials.** Example configs are for developers; the actual config comes from env vars. `.env` is in `.gitignore`.
- **AGENTS.md Local Contracts are binding.** If a later agent reads AGENTS.md and sees "no-interruption rule is absolute, do not reorder", you must actually enforce it in code, not just document it. If you can't enforce it in code, don't promise it in AGENTS.md.
- **After all files are written, run pytest AND ruff before git push.** A green test suite with lint failures is not a clean commit. Fix both.

## User preferences (this user)

- "do that now" / "continue" = full execution, no intermediate pauses
- Wants everything in one go: PRD, code, tests, docs, git push, issue
- Values AGENTS.md with binding Local Contracts (enforced in code, not just documented)
- Trusts the agent to make all tier-2 decisions (module names, class hierarchies, framework choices, file layout)
- Wants fast pivots: if a test fails, fix it and re-run — don't stop to ask about the failure
