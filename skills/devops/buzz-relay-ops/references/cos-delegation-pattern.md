# Chief of Staff — Buzz Delegation + Smart Routing

Pattern for a Chief of Staff agent operating on a Buzz (Nostr) relay, delegating to
specialist agents via @mention, and using cost-optimized smart model routing through OmniRoute.

## Model Architecture: Free-First, Smart Routing

### Agent Workhorse Combo (all non-CoS agents)

Cost-optimized fallback chain. Free tier handles 90%+ of volume:

```
Priority 1: oc/deepseek-v4-flash-free      FREE — OpenCode Zen
Priority 2: opencode-go/deepseek-v4-flash   PAID — Go subscription
Priority 3: yunwu/deepseek-v4-flash         PAID — YunWu (last resort)
Priority 4: openrouter/google/gemma-4-31b-it:free  FREE — emergency
```

Estimated monthly cost for 45 agents: under $1. Free DeepSeek handles routine queries
(status checks, channel replies, simple lookups). Paid tiers only fire on overflow.

### CoS Smart Combo

Auto-escalating fallback. OmniRoute handles model selection — no query classifier needed:

```
Priority 1: yunwu/deepseek-v4-flash    → handles routine queries (~80%)
Priority 2: yunwu/gpt-5.6-sol          → auto-kicks in on error/timeout/complexity
Priority 3: yunwu/gpt-5.6-sol-max      → extreme complexity only
```

If DeepSeek returns an error, timeout, or rate limit, OmniRoute automatically
falls to GPT 5.6 SOL. The CoS doesn't classify its own queries — the combo
fallback IS the smart routing.

### Mixed/Uniform Model Policy

Uniform by default: all agents get `agent-workhorse-combo`. Mixed by exception:
a YAML manifest lists per-agent overrides with rationale.

| Agent | Override | Reason |
|-------|----------|--------|
| dev-lead | yunwu/deepseek-v4-pro | Code generation needs depth |
| nova | yunwu/deepseek-v4-pro | Deep research |
| history-lead | oc/deepseek-v4-flash-free | Documentation is simple |
| security-lead | oc/deepseek-v4-flash-free | Health checks are simple |

Implementation: `scripts/apply_agent_models.py` — batch applier with `--dry-run`,
respects `config/agent-model-overrides.yaml` for exceptions.

## Delegation Pattern on Buzz

### Basic Flow

the operator interacts ONLY with the Chief of Staff. CoS delegates via @mention:

```
the operator in #admin: "@Chief get me an update on MES pipeline"
CoS in #revenue: "@Revenue what's the MES pipeline status?"
Revenue in #revenue: "3 active leads, 1 contract pending. ETA Friday."
CoS in #admin: "MES pipeline: 3 active, 1 contract pending (ETA Friday). Revenue Lead has details."
```

### Key Mechanics

- CoS has visibility into ALL team channels (30+ channels in `buzz_keys.json`)
- @mention any agent in any channel to pull them into a discussion
- Agents reply in the same channel — CoS reads the reply
- Bridge handles @mention → OmniRoute → reply with agent's own Nostr key
- Anti-loop: agent pubkey filter + SEEN set + reply text filter prevents cycles

### CoS AGENTS.md Requirements

The CoS AGENTS.md must document:
1. **Buzz platform operation** — crypto-signed messages, UUID channels, bridge dependency
2. **Smart routing** — when DeepSeek is used vs when GPT 5.6 SOL auto-kicks in
3. **Channel visibility tiers** — P0 through P3 with scan frequency
4. **Delegation examples** — concrete @mention flows with expected responses
5. **Daily brief compilation** — step-by-step process from lead summaries to compiled brief
6. **Tone rules** — direct, concise, decision-oriented, never sycophantic

### Platform Differences (Discord → Buzz)

| Aspect | Discord | Buzz |
|--------|---------|------|
| Identity | Single bot token per agent | Ed25519 keypair per agent |
| Messages | Plain text via API | Cryptographically signed Nostr events |
| Channels | Discord channel ID | UUID (resolved via `buzz_channels.json`) |
| @mention | Discord ping | Bridge text-match on alias |
| History | Discord API | Nostr relay query (kind 9 + author filter) |
| Auth | Bot token in header | NIP-42 challenge-response per connection |
| Audit trail | Discord audit log | Immutable signed events in Postgres |

## Pitfalls

### CoS overwhelmed by 30+ channels
**Symptom:** CoS tries to read every message in real time.
**Fix:** Three-tier summarization — leads summarize daily, CoS compiles, deep dive on demand.
Channel scan cron stays silent unless 🚨.

### Bridge is single point of failure
**Symptom:** Bridge dies, all @mentions silently drop.
**Fix:** Watchdog cron (15m, no_agent, detached spawn). Guardian-angel monitors bridge PID.
Keep emergency escalation path on Discord (gateway process independent of OmniRoute).

### Wrong model used for CoS
**Symptom:** CoS config.yaml uses free tier or invalid bearer.
**Fix:** CoS profile must use `provider: custom:omniroute` with real `sk-` API key.
Default model routes through `cos-smart-combo`. Verify with authenticated probe to OmniRoute.

### CoS can't see agent replies
**Symptom:** CoS delegates but never sees the response.
**Fix:** CoS `buzz_keys.json` entry must include ALL team channels, not just admin/supervisor/general.
Re-run `buzz_invite_agents.py` for CoS across new channels after updating keys.
