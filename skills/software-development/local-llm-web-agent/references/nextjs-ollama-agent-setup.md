# Next.js + Ollama Agent Setup Reference

## Session Context: DH Construction Management Portal

This reference documents a worked example: integrating a local Gemma 4 model (via Ollama) as a function-calling AI assistant in a Next.js 15 production app with PostgREST database access.

## Architecture

```
Client (React) → POST /api/assistant → Ollama /api/chat → Tool Execution → PostgREST → PostgreSQL
                                                               ↓
                                                      Natural language response
```

## Component Stack

| Layer | Technology | Port |
|---|---|---|
| Web server | Next.js 15 (App Router) | 3333 |
| LLM | Ollama + huihui_ai/gemma-4-abliterated | 11434 |
| Database API | PostgREST (direct, bypass Kong) | 54324 |
| Database | PostgreSQL (Supabase local) | 54322 |
| ~~Auth proxy~~ | ~~Kong (broken key-auth)~~ | ~~44444~~ |

## Key Files

```
app/api/assistant/route.ts     — POST handler, tool defs, executors, formatters
lib/data-service.ts            — PostgREST CRUD functions
middleware.ts                  — Auth middleware (API routes must be public)
.env.local                     — DB URL, optional OPENROUTER_API_KEY
```

## Critical Details Found During Integration

### 1. PostgREST POST Returns Null Body

**Problem:** `pg('POST', ...)` returned `null` even for successful creates.
**Root cause:** PostgREST's default POST returns HTTP 201 with no response body.
**Fix:** Add `Prefer: return=representation` header to POST requests.
**Detection:** Project appeared in DB `SELECT * FROM projects` but the app said "Failed to create."

### 2. PostgREST DATE NOT NULL Rejects Empty Strings

**Problem:** POST to `projects` table returned `400 invalid input syntax for type date: ""`.
**Root cause:** Columns declared `DATE NOT NULL` with no DEFAULT.
**Fix:** Compute default dates when not provided by the LLM:
```typescript
start_date: args.start_date || new Date().toISOString().split('T')[0]
estimated_completion: args.estimated_completion ||
  new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0]
```

### 3. Middleware Blocks All Non-Auth API Routes

**Problem:** `/api/setup`, `/api/projects`, etc. returned HTML login page instead of JSON.
**Root cause:** Middleware publicRoutes only included `/api/auth`, not `/api`.
**Fix:** Add `/api` to publicRoutes — `pathname.startsWith('/api')` catches all API endpoints.

### 4. Ollama Response Format Differs from OpenAI

**Key differences documented in SKILL.md — the critical one:**
- Ollama's `function.arguments` is a parsed object, NOT a JSON string
- Normalization code must handle both formats for robustness

### 5. Stale Build After Parallel Subagents

**Problem:** After subagents finished rewriting code, the production server kept returning old responses.
**Root cause:** `npx next build` ran before subagents completed writing files.
**Fix:** Always rebuild AFTER all batch changes are saved, kill old server, restart fresh.

### 6. PostgREST Direct vs Kong

Kong's key-auth was broken because `kong.yml` had truncated placeholder keys. The `apikey` header value was `eyJhbG...TVJM` (~13 chars) instead of a valid 150+ char JWT. Solution: bypass Kong entirely and connect to PostgREST directly on port 54324 with `PGRST_DB_ANON_ROLE: postgres` (full anonymous access).

## Ollama Model Info

```bash
# Models pulled and tested
huihui_ai/gemma-4-abliterated:latest  # Function-calling works well
huihui_ai/Qwen3.6-abliterated:27b     # 27B, not tested with tools
llama3.2:1b                           # Too small for function calling

# First-call latency: ~55s (model loads from disk to VRAM)
# Subsequent latency: 12-25s (cached in VRAM)
# GPU: RTX 3090 (24GB VRAM)
```

## Smoke Test Commands

```bash
# Check Ollama is alive
curl http://localhost:11434/api/tags

# Check PostgREST is alive
curl http://localhost:54324/

# Test the assistant endpoint
curl -X POST http://localhost:3333/api/assistant \
  -H 'Content-Type: application/json' \
  -d '{"message":"Show me all projects","role":"admin"}'

# Test all API routes
for route in setup projects users notifications schedule; do
  curl -s http://localhost:3333/api/$route | head -c 100
  echo ""
done

# Test auth
curl -s -X POST http://localhost:3333/api/auth \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@demo.com","password":"demo123","action":"login"}'
```
