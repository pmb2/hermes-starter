# OpenAI Record & Replay — FOSS Architecture

## What OpenAI's Feature Does

Record & Replay captures full agent sessions (LLM calls, tool invocations,
intermediate states) and replays them deterministically for debugging.
Think time-travel debugger for agent workflows.

Three layers:
1. **Tracing** — capture everything that happens in a session
2. **Replay** — re-run with cached responses to isolate bugs
3. **Evaluation** — compare runs, detect regressions, score outputs

## What Hermes Already Has (state.db)

### sessions table
id, source, model, model_config, system_prompt, parent_session_id,
started_at, ended_at, end_reason, message_count, tool_call_count,
input/output/reasoning/cache tokens, estimated/actual cost, title, cwd,
api_call_count, archived, rewind_count

### messages table
session_id, role (user/assistant/tool), content, tool_call_id, tool_calls,
tool_name, timestamp, token_count, finish_reason, reasoning, reasoning_content,
reasoning_details, platform_message_id, observed, active, compacted

**Verdict:** Hermes already has better session recording than most FOSS tools.
The data is there. Missing: replay engine, diff comparison, debugging UI.

## FOSS Alternatives Landscape

| Tool | License | Stars | Record | Replay | Diff | View | Self-Host |
|------|---------|-------|--------|--------|------|------|-----------|
| **Langfuse** | MIT | 10k+ | ✓ Sessions | ✓ UI step | ✗ | ✓ | Docker+PG |
| **Arize Phoenix** | BSD-3 | 10k+ | ✓ Traces | ✗ | ✓ Exps | ✓ | pip+Docker |
| **OpenLLMetry** | Apache-2 | 5k+ | ✓ OTLP | ✗ | ✗ | ✗ | Transport |
| **Braintrust** | Elastic | 3k+ | ✓ Sessions | ✓ Basic | ✗ | ✓ | Cloud |

## Required Components

### 1. Deterministic Replay Engine (BUILD)
Loads a session from state.db and replays each turn:
- LLM calls → return CACHED response from original run
- Tool calls → re-run OR return cached result
- Creates replay session linked via parent_session_id

### 2. Diff Engine (BUILD)
Compare two sessions:
- Token-level LLM output diff
- Tool call parameter diff
- Timing/cost diff

### 3. Trace Viewer (BUILD or Integrate)
Options: Langfuse (self-hosted), Phoenix, or built-in TUI

## Implementation Roadmap

**Phase 1 (Week 1-2):** `cached_responses` table, replay CLI
**Phase 2 (Week 3-4):** `diff_sessions()`, compare CLI
**Phase 3 (Week 5-6):** Langfuse/Phoenix OTLP export
**Phase 4 (Week 7-8):** LLM-as-judge evaluation pipeline
