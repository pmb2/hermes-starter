# OpenCode ACP Protocol Reference

OpenCode v1.15.6+ implements ACP (Agent Client Protocol) over stdin/stdout via `opencode acp`.
This is the same JSON-RPC 2.0 protocol used by the GitHub Copilot ACP client.

## Protocol Flow (per task)

```
Hermes                          OpenCode (opencode acp)
  │                                   │
  │── initialize ────────────────────→│
  │←── result (protocolVersion, ...) ─│
  │                                   │
  │── session/new ───────────────────→│
  │←── result (sessionId, models, ...)│
  │                                   │
  │── session/prompt ────────────────→│
  │←── session/update (chunks)  ──────│  (streaming)
  │←── session/update (chunks)  ──────│
  │←── result ────────────────────────│
  │                                   │
  │── close (implicit via process)    │
```

## Initialize Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": 1,
    "clientCapabilities": {
      "fs": {
        "readTextFile": true,
        "writeTextFile": true
      }
    },
    "clientInfo": {
      "name": "hermes-agent",
      "title": "Hermes Agent",
      "version": "0.0.0"
    }
  }
}
```

### Initialize Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": 1,
    "agentCapabilities": {
      "loadSession": true,
      "mcpCapabilities": { "http": true, "sse": true },
      "promptCapabilities": { "embeddedContext": true, "image": true },
      "sessionCapabilities": { "close": {}, "fork": {}, "list": {}, "resume": {} }
    },
    "authMethods": [
      {
        "description": "Run `opencode auth login` in the terminal",
        "name": "Login with opencode",
        "id": "opencode-login"
      }
    ],
    "agentInfo": {
      "name": "OpenCode",
      "version": "1.15.6"
    }
  }
}
```

## Session/New Request

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "session/new",
  "params": {
    "cwd": "C:\\Users\\<you>",
    "mcpServers": []
  }
}
```

### Session/New Response

Returns `sessionId`, `configOptions` (model picker, mode picker), `models` (current + available),
and `modes` (build/plan). The response is large — includes the full model catalog from all
configured providers.

Key fields:
- `result.sessionId` — the session identifier (e.g. `ses_1b4f60f7fffeikIo1qEblBAbDG`)
- `result.models.currentModelId` — e.g. `opencode-go/minimax-m2.5`
- `result.models.availableModels` — all models OpenCode can use
- `result.modes.currentModeId` — `"build"` or `"plan"`

## Session/Prompt Request

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "session/prompt",
  "params": {
    "sessionId": "ses_...",
    "prompt": [
      { "type": "text", "text": "Your prompt here..." }
    ]
  }
}
```

### Server-Sent Events (session/update)

During prompt processing, the server sends streaming updates:

```json
{
  "jsonrpc": "2.0",
  "method": "session/update",
  "params": {
    "update": {
      "sessionUpdate": "agent_message_chunk",
      "content": { "text": "I'll implement that..." }
    }
  }
}
```

Types:
- `agent_message_chunk` — text response chunks (collected into `text_parts`)
- `agent_thought_chunk` — reasoning/thinking chunks (collected into `reasoning_parts`)

### Server Requests (fs/, session/)

During execution, OpenCode may send server-side requests back to the client:

- `session/request_permission` — asking for approval (Hermes auto-denies)
- `fs/read_text_file` — read file content (Hermes responds with file content)
- `fs/write_text_file` — write file content (Hermes performs the write)

## Stats Endpoint

```sh
# Box-drawing TUI output showing sessions, messages, costs, tokens
opencode stats
opencode stats --days 30
opencode stats --models 5
opencode stats --project .

# Sample output shape:
# OVERVIEW: 59 sessions, 9548 messages, 30 days
# COST & TOKENS: Total $36.26, Input 225.3M, Output 2.8M
# MODEL USAGE: per-model breakdown
```

## Session Export

```sh
opencode export <sessionID>             # Full JSON
opencode export <sessionID> --sanitize  # Redacted
opencode session list                   # Discover session IDs
```

Export JSON structure:
```json
{
  "info": {
    "id": "ses_...",
    "title": "Session title",
    "agent": "build",
    "model": { "id": "minimax-m2.5", "providerID": "opencode-go" },
    "cost": 0.45576345,
    "tokens": {
      "input": 805456,
      "output": 16821,
      "cache": { "read": 6464715, "write": 60673 }
    },
    "time": { "created": 1779369950584, "updated": 1779373832956 }
  },
  "messages": [
    {
      "info": {
        "role": "user",
        "time": { "created": ... },
        "agent": "build",
        "model": { "providerID": "opencode-go", "modelID": "minimax-m2.5" },
        "id": "msg_...",
        "sessionID": "ses_..."
      },
      "parts": [
        { "type": "text", "text": "User message content..." }
      ]
    },
    {
      "info": {
        "role": "assistant",
        "mode": "build",
        "cost": 0.0008892,
        "tokens": { "total": 62794, "input": 1840, "output": 281 },
        "modelID": "minimax-m2.5",
        "providerID": "opencode-go",
        "time": { "created": ..., "completed": ... },
        "finish": "tool-calls"
      },
      "parts": [
        { "type": "step-start", ... },
        { "type": "text", "text": "Assistant response..." },
        { "type": "tool-call", ... }
      ]
    }
  ]
}
```

## Key Differences from Copilot ACP

| Aspect | Copilot ACP | OpenCode ACP |
|--------|-------------|--------------|
| Command | `copilot --acp --stdio` | `opencode acp` |
| Auth | Copilot subscription | `opencode auth login` / provider config |
| Model | Subscription-gated | Config-driven (any provider in auth list) |
| Session Config | Minimal | Returns full model picker + mode selector |
| Init Response | Basic capabilities | Includes `authMethods` array |
