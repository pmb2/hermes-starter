# Profiles

Profiles are isolated Hermes instances: each has its own config, skills, memories,
sessions, and even its own gateway identity. This is how you run a **multi-agent team**
on one machine.

```
hermes profile create chief-of-staff
hermes -p chief-of-staff        # run as that profile
hermes profile list
```

## What's in this dir

**`chief-of-staff/AGENTS.md`** — an example persona charter for a coordinator agent.
It defines:

- **Mission** — what the agent exists to do
- **Reporting lines** — who it answers to (marketing lead, dev lead, ops…)
- **Operating rules** — approval gates, escalation paths, communication style
- **Quality bar** — what "done" means

An `AGENTS.md` in a profile's root is loaded into every session of that profile,
giving the agent stable identity across conversations.

## Building a team

The pattern that works well:

| Profile | Charter focus |
|---------|---------------|
| `chief-of-staff` | Coordination, escalation, daily briefs |
| `dev-lead` | Code review, engineering pulse, repo hygiene |
| `analyst` | Intel digestion, cross-referencing, reporting with URLs |
| `ops` | System health, containers, updates, watchdogs |

Each profile can also have its own `config.yaml` with a different model + persona.
Copy `profiles/chief-of-staff/AGENTS.md` and edit.

## Pitfalls (learned the hard way)

- Profile `config.yaml` is **shallow-merged** onto the root config. An incomplete
  `model:` section (missing `api_mode`/`base_url`) silently falls back to a default
  provider. Include all four fields: `api_mode`, `base_url`, `default`, `provider`.
- `.env` keys do **NOT** propagate into profile gateways. If a profile needs keys,
  give it its own `.env` inside its profile dir.
- YAML `@` values must be quoted (`'@name/thing'`) or the whole profile config fails
  to parse and is ignored.
- Memory is per-profile — profiles don't share what they've learned unless you
  deliberately export/import.

Full profile docs: `hermes profile --help` and the skill at
`skills/autonomous-ai-agents/hermes-agent/SKILL.md`.