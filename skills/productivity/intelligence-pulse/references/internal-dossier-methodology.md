# Internal Dossier Compilation Methodology

**Purpose:** When the user asks for a "dossier", "executive summary", "profile", or deep synthesis on a known entity (person, company, project, organization), compile a structured dossier using **only internal knowledge stores** — no external web research needed. The answer is already in the system; you just need to extract and synthesize it.

## When to Load

- User asks: "give me a dossier on [entity]", "who is [entity]", "executive summary on [entity]", "profile [entity]", "tell me about [entity]"
- User asks for a "dossier styled" report
- Entity is someone/something the user has already interacted with (not a fresh unknown)

## Data Sources (check in this order)

| Priority | Source | What It Contains | How to Access |
|----------|--------|-----------------|---------------|
| 1 | **Memory (your notes)** | Persistent environment facts, project conventions, tool quirks, infrastructure details | Already loaded in context |
| 2 | **User profile** | User preferences, communication style, tech setup, operating constraints | Already loaded in context |
| 3 | **Session history** | Past conversations, tasks completed, decisions made, bugs fixed | `session_search()` — browse first, then query |
| 4 | **MemPalace** | Semantic memory — 10K+ drawers, wings/rooms/tunnels, detailed session content | `mempalace_search()` + `mempalace_list_wings()` |
| 5 | **GBrain** | Structured knowledge, graph traversal, page hierarchy, takes/claims | `mcp_gbrain_query()`, `mcp_gbrain_find_experts()`, `mcp_gbrain_list_pages()`, `mcp_gbrain_search()` |
| 6 | **Past work artifacts** | Agent definitions, soul.md, AGENTS.md files, project READMEs, command OS architecture | `search_files()` on project directories, `read_file()` on key documents |

## Dossier Format Template

```markdown
## 📋 CONFIDENTIAL DOSSIER
### Subject: [Entity Name]

**Classification:** INTERNAL | **Date:** [Date] | **Compiled by:** Hermes Agent (Intelligence Arm)

---

### 1. EXECUTIVE IDENTITY

| Field | Detail |
|---|---|
| **Known As** | [Aliases, handles] |
| **Role** | [Primary function/identity] |
| **Primary Domain** | [Core expertise area] |
| **Base of Operations** | [Location/environment] |
| **Operating Model** | [How they operate] |

**Summary:** [2-3 sentence synthesis of who they are]

---

### 2. ORGANIZATIONAL ARCHITECTURE (if applicable)

[Hierarchy diagram or relationship map]

---

### 3. INFRASTRUCTURE FOOTPRINT (if applicable)

[Systems, tools, environments they maintain]

---

### 4. PROFESSIONAL DOMAINS (if a person)

| Domain | Depth | Notes |
|---|---|---|
| [Domain 1] | [Expert/Intermediate/Novice] | [Details] |
| [Domain 2] | [Expert/Intermediate/Novice] | [Details] |

---

### 5. OPERATING STYLE & PREFERENCES

[Communication patterns, work rhythm, tech preferences, values]

---

### 6. ACTIVE WORKSTREAMS / PIPELINES

| Stream | Status | Tooling |
|---|---|---|
| [Stream 1] | [Active/Stalled/Planned] | [Tools used] |
| [Stream 2] | [Active/Stalled/Planned] | [Tools used] |

---

### 7. KEY RELATIONSHIPS & DEPENDENCIES

| Entity | Type | Relationship |
|---|---|---|
| [Entity] | [Tool/Partner/Platform] | [How they relate] |

---

### 8. RISK PROFILE & EDGE CASES

| Factor | Notes |
|---|---|
| [Risk 1] | [Description] |
| [Risk 2] | [Description] |

---

### 9. ASSESSMENT

[Executive-level synthesis — 1 paragraph. What's notable, what phase are they in, what's the key constraint or opportunity?]

---

*Dossier compiled from [X] data sources. Intelligence confidence: [HIGH/MEDIUM/LOW] (source-grounded).*
```

## Synthesis Principles

1. **Sources first, then synthesis** — gather from all sources before writing. Don't jump to conclusions from one source.
2. **Ground every claim** — Each assertion should be traceable to a specific source (memory entry, session id, gbrain slug, mempalace drawer, file path).
3. **Know what you don't know** — If a section is empty or speculative, say so. Confidence annotations (HIGH/MEDIUM/LOW per claim) are better than false certainty.
4. **Dossier is for the subject** — Organize everything around the entity being dossiérsed. Don't digress into the user's other activities unless they're directly relevant.
5. **End with an assessment** — The dossier should answer "so what?" at the end. The assessment is your synthesis of what this entity means for the user.
6. **Keep it lean** — Executive level means scannable. Use tables, bold key numbers, and keep prose tight.
