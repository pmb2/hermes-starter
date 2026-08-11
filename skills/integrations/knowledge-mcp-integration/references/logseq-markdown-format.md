# Logseq Markdown Format Reference

Logseq stores each graph as standard markdown files in a flat directory
structure. The File MCP server reads/writes these files directly, no API
needed.

## Directory Structure

```
~/.logseq/<graph-name>/
├── pages/              # Page files — page_name.md
├── journals/           # Daily journal entries — YYYY_MM_DD.md
└── logseq/             # Logseq config — config.edn (Clojure EDN)
```

## Page File Format

```markdown
type:: concept
tags:: #tag1 #tag2 #hermes
created:: 2026-01-01T00:00:00Z

## Page Title
First block — body content with [[wikilinks]] and #tags.

Second block — additional content separated by blank line.

id:: 550e8400-e29b-41d4-a716-446655440000
Third block with explicit UUID assigned by Logseq.
```

## Journal File Format

```markdown
created:: 2026-07-30T00:00:00Z

#journal #milestone

Journal entry content here.

[[Linked Page]] reference in journal.
```

## Key Syntax Rules

| Feature | Syntax | Example |
|---|---|---|
| Properties | `key:: value` at top of file | `type:: concept` |
| Wikilinks | `[[Page Name]]` | `[[Hermes Agent]]` |
| Tags | `#tagname` | `#hermes #mcp` |
| Block IDs | `id:: <uuid>` on its own line | `id:: 550e8400-e29b-41d4-a716-446655440000` |
| Block refs (cross-linking) | `((<uuid>))` | `((550e8400-e29b...))` |
| TODOs | `- TODO` / `- DONE` | `- TODO Write docs` |
| Nested blocks | `- item\n  - sub-item` (indented) | Indent 2 spaces per level |
| Markdown | Standard GFM | Headers, lists, code, tables |

## Property Parsing Behavior

Lines matching `^\w[\w-]*::\s*(.*)` at the top of a file are treated as
properties (Logseq frontmatter). The parser stops at the first
non-property, non-blank line. This means blocks below the property section
can use `::` in their content without conflict (e.g. timestamps, code).

```
type:: concept          ← property
tags:: #test             ← property

This block contains :: and it's fine.  ← body content (parsing stopped)
```

## Filename Normalization

Logseq normalizes page names to filenames aggressively:

| Page Title | Filename |
|---|---|
| Knowledge Architecture | `knowledge_architecture.md` |
| MCP Integration Notes | `mcp_integration_notes.md` |
| Customization Guide | `customization_guide.md` |
| Hermes Agent 2.0 | `hermes_agent_2_0.md` |
| Special Chars: $@#! | `special_chars_.md` |

Rules: lowercase, spaces→underscores, non-alphanumeric→underscores.

## Case-Insensitive Lookup

Page titles are case-insensitive. "CUSTOMIZATION GUIDE" should resolve
to `customization_guide.md`. The MCP server maintains a lookup map keyed
by both the display title and the slug.

## Bidirectional Links (Graph)

Logseq's linking model:

```
Page A contains [[Page B]] and [[Page C]]
    →  A.links_out = ["Page B", "Page C"]
    →  B.links_in  = ["Page A"]
    →  C.links_in  = ["Page A"]
```

A graph query builds:
- **Nodes**: All pages with title, tags, block count
- **Edges**: `{source: "Page A", target: "Page B"}` for each [[link]]

**Backlinks** are computed by scanning all pages for [[Page Name]]
references — they are NOT stored explicitly.

**Orphans** are pages with no links_in AND no links_out (no bidirectional
connections at all). These may be stub pages or disconnected content.

## Block Structure (for Block-Level Operations)

A Logseq page is parsed as:

```
[properties dict]
[block 0, block 1, ..., block N]
```

Each block is separated by one or more blank lines. Blocks can contain:
- Plain text
- Markdown formatting
- [[Wikilinks]]
- #Tags
- Bullet lists (`- item`, `* item`)
- `id:: <uuid>` for block identity

Block operations:
- **Create**: insert a new block at an index position (0 = first, append = last)
- **Read**: return blocks by index with content preview
- **Update**: replace a block's content (preserving its ID if present)
- **Delete**: remove a block and shift remaining blocks up

## File-Based MCP Server Architecture

```
┌─────────────┐    stdio     ┌──────────────────┐    filesystem    ┌──────────────┐
│ Hermes Agent │ ◄─────────► │ Logseq File MCP  │ ◄─────────────► │ ~/.logseq/   │
│ (tools)      │             │ (17 tools)       │                 │ hermes-graph/ │
└─────────────┘              └──────────────────┘                 └──────────────┘
```

Key design decisions:
- **No caching**: Every tool call reads the file fresh — keeps data
  consistent but means write-heavy workloads are slower.
- **No file locking**: Single-agent use only. Multi-agent would need
  `msvcrt.locking()` on Windows or `fcntl.flock()` on Unix.
- **Properties stripped from blocks**: The properties dict is separate
  from the block list. `get_page` returns both; `get_page_blocks` returns
  only the body blocks.
- **Block UUIDs**: If a block doesn't have `id:: <uuid>`, the create_block
  tool injects one. Update/delete by index, not by UUID.
