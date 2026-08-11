# BOOTSTRAP — Zero to Running Agent

This guide takes a fresh machine to a working Hermes Agent with a Discord gateway,
channel personas, cron jobs, and (optionally) a Buzz bridge. Time: **~30 minutes**.

---

## 0. Prerequisites

| Requirement | Why | Check |
|-------------|-----|-------|
| Windows 10/11 (or Linux / WSL2 / macOS) | Hermes runs everywhere | — |
| Python 3.11+ | Hermes runtime | `python --version` |
| Node.js 20+ | npx-based MCP servers (optional) | `node --version` |
| Git | cloning this repo | `git --version` |
| An LLM API key | the brain | OpenRouter/DeepSeek/OpenAI/any |
| A Discord account + server | the chat frontend | you own a server |

> **LLM provider:** the example config ships pointed at a local OmniRoute-style gateway
> (`http://localhost:20128/v1`) with an OpenRouter/DeepSeek fallback chain. If you don't
> run a local router, just change `model.base_url` + `model.api_key` (or set
> `OPENROUTER_API_KEY` in `.env` and switch `model.provider` to `openrouter`).
>
> **Platform note:** the author runs Windows + git-bash, so `scripts/*.sh` are written
> for that. On Linux/macOS they run as-is (bash); only paths in `.env` and
> `config.example.yaml` (e.g. `C:\Users\<you>\AppData\Local\hermes`) need the native
> equivalent (`~/.local/share/hermes` on Linux). Everything else is portable.

---

## 1. Install Hermes Agent

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

On Windows, run that inside **git-bash**. Then verify:

```bash
hermes --version
hermes doctor          # checks dependencies and config
```

Follow the prompts of `hermes setup` **once** to pick your primary model provider —
or skip it and edit config directly (step 4).

---

## 2. Clone the Starter Kit

```bash
git clone https://github.com/pmb2/hermes-starter.git
cd hermes-starter
```

---

## 3. Install Config, Skills, Scripts, Plugins

```bash
bash scripts/setup.sh
```

This copies:

- `config/config.example.yaml` → `~/AppData/Local/hermes/config.yaml` (Windows) or `~/.hermes/config.yaml` (Linux/macOS)
- `skills/` → your Hermes home `skills/` (won't overwrite existing skills)
- `scripts/` → Hermes home `scripts/` (cron + watchdogs resolve here)
- `plugins/` → Hermes home `plugins/`
- `prompts/`, `templates/` → Hermes home `prompts/`, `templates/`
- `profiles/` → Hermes home `profiles/` (example personas)

> The install is idempotent — re-running won't clobber things you've changed.
> Set `HERMES_HOME` first if you want a custom location.

---

## 4. Secrets — `.env`

```bash
cp .env.example ~/AppData/Local/hermes/.env     # Windows
# or: cp .env.example ~/.hermes/.env            # Linux/macOS
```

Edit it and fill in **your** values:

```bash
# ── Model provider (pick one) ──
OPENROUTER_API_KEY=sk-or-...          # or DEEPSEEK_API_KEY / OPENAI_API_KEY / etc.

# ── Discord ──
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_HOME_CHANNEL=your-home-channel-id
```

Never commit this file. It's gitignored.

---

## 5. Create a Discord Bot

1. Go to <https://discord.com/developers/applications> → **New Application** → name it.
2. **Bot** tab → **Reset Token** → copy the token. (That's `DISCORD_BOT_TOKEN`.)
3. Under **Privileged Gateway Intents**, enable **Message Content Intent** —
   without it the bot can't read messages and will be silent. (Server Members Intent too
   if you use `DISCORD_ALLOWED_USERS`.)
4. **OAuth2 → URL Generator**: scope `bot`, permissions: `Send Messages`,
   `Read Messages/View Channels`, `Embed Links`, `Attach Files` — open the URL, invite
   the bot to your server.

Verify the bot joined: it should appear in your server's member list.

---

## 6. Channel IDs + Personas

Enable **Developer Mode** in Discord (Settings → Advanced → Developer Mode), then
right-click a channel → **Copy Channel ID**.

In `config.yaml`:

```yaml
discord:
  require_mention: true
  channel_prompts:
    '<discord-channel-id-1>': 'You are Dev, the Development Lead. ...'
    '<discord-channel-id-2>': 'You are Intel, the Intelligence Lead. ...'
    '<discord-channel-id-3>': 'You are Ops, the Infrastructure Lead. ...'
```

- Replace the `<discord-channel-id-N>` placeholders with real channel IDs.
- `channel_prompts` = per-channel agent identities. In a channel with a prompt, the
  agent **auto-responds**; in channels without one, it replies only when @mentioned
  (`require_mention: true`).
- Set `DISCORD_HOME_CHANNEL` in `.env` to the channel where scheduled/undirected
  messages should land.

---

## 7. Start the Gateway

```bash
hermes gateway run          # foreground — watch it connect (Ctrl+C to stop)
# once confirmed working:
hermes gateway install      # background service
hermes gateway start
hermes gateway status
```

Logs: `~/AppData/Local/hermes/logs/gateway.log` (Windows) or `~/.hermes/logs/gateway.log`.

Then go to your Discord server and talk to your agent in the persona channels.
Use `/restart` in Discord after any config change.

---

## 8. Optional: Multi-Agent Profiles

Each profile is an isolated agent with its own config, skills, memories, and sessions:

```bash
hermes profile create chief-of-staff
hermes -p chief-of-staff        # chat as that profile
```

The kit ships an example `profiles/chief-of-staff/AGENTS.md` — a persona charter that
defines an agent's role, reporting lines, and operating rules. Copy the pattern for your
own team (dev lead, analyst, ops…).

> Profile gotcha: profile `config.yaml` is **merged shallowly** with the root config —
> a profile's `model:` section must include `api_mode`, `base_url`, `default`, `provider`
> or it silently falls back. And `.env` keys do **not** propagate into profile gateways —
> give each profile its own `.env` if it needs keys.

---

## 9. Optional: Cron Jobs

The kit ships a seed file you can import into the scheduler (see `cron/README.md`)
or create jobs interactively:

```bash
hermes cron create 'every 4h' --prompt "Heartbeat: check git activity, report briefly, stay silent if nothing changed"
hermes cron list
```

Cron scripts resolve relative to your Hermes home `scripts/` directory.

---

## 10. Optional: Buzz Bridge (agent identities on a relay)

The **Buzz bridge** gives every agent its own Nostr identity on a local relay —
message agents by @mention with no single shared account.

1. Install a local Buzz relay (see `gateway/buzz.md`).
2. Generate identities: `python scripts/generate_buzz_keys.py` → creates fresh keypairs
   (never reuse anyone else's).
3. Start: `python scripts/start_buzz_bridge.py` (auto-restarts, logs to `bridge.log`).
4. Add a watchdog cron: `hermes cron create 'every 15m'` with
   `--no-agent --script buzz_watchdog.py`.

Each agent responds from its **own** key, so replies are attributable per-persona.

---

## 11. Verify Everything

```bash
hermes doctor                 # health check
hermes gateway status         # gateway up?
hermes cron list              # jobs scheduled?
hermes status                 # component summary
```

Then test the loop: message your bot in a persona channel → it should reply within
seconds, using the channel's persona.

---

## Next Steps

- **Teach it your world:** `/new` sessions + memory build up automatically. The
  `memory` tool persists facts about you across sessions — that's how it learns.
- **Install more skills:** `hermes skills browse` / `hermes skills install <id>`.
- **Add MCP servers** for tools/APIs: `hermes mcp add NAME` (examples in
  `config/config.example.yaml`).
- **Extend cron** with your own pipelines — the seed jobs show the pattern.
- **PR back:** found a better watchdog, fixed a script? Open a PR — this kit is meant to
  keep improving for everyone.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Bot silent in Discord | Enable **Message Content Intent** (step 5), restart gateway |
| `503/429` model errors | Check `.env` key, check fallback chain in config |
| Config changes not applying | `/restart` in Discord or `hermes gateway restart` |
| `Script not found` in cron | Script must live under Hermes home `scripts/` (no nested `scripts/scripts`) |
| First-run HTTP 400 model error | config.yaml saved with BOM — re-save UTF-8 without BOM (use `hermes config edit`) |
| Voice/TTS not working | `hermes config set stt.enabled true`; pip install faster-whisper for local STT |

See the `hermes-agent` skill (shipped in this kit under `skills/`) for deep
troubleshooting.