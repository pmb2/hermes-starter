# Agent Scaffold — Canonical Template

Every agent in agent-universe follows this exact structure. Used when creating new agents to ensure consistency.

## Directory Layout
```
agent-name/
├── AGENTS.md
├── README.md
├── config/config.yaml
├── .env.example
├── tooling/.gitkeep       (or scripts/)
├── templates/.gitkeep
├── docs/.gitkeep
└── tests/.gitkeep
```

## AGENTS.md Template
```markdown
---
name: agent-name
team: "NN — Team Name"
repo: agent-repo-name
version: 0.1.0
status: seed
---

# Agent: Human-Readable Name

- **Team:** NN — Team Name
- **Repo:** `agent-repo-name`

## Role
Brief description of this agent's role in the team.

## Key Capabilities
1. Capability one
2. Capability two
3. Capability three

## Tooling
- `tool-name` — description

## MCP Servers
- `server-name` — purpose
```

## README.md Template
```markdown
# Agent Name

Team: NN — Team Name · Repo: agent-repo-name

## Overview
Short description.

## Prerequisites
- Python 3.10+
- Dependencies

## Quick Start
```bash
# Basic usage
python tooling/script.py --arg value
```

## See Also
- [Related Agent](../related-agent/)
- [Cross-team Reference](../shared/component/)
```

## config/config.yaml Template
```yaml
agent:
  name: agent-name
  version: 0.1.0
  log_level: info
  output_dir: ./tooling/output
mcp_servers:
  postgres:
    transport: stdio
  filesystem:
    transport: stdio
```

## .env.example Template
```
# Target
TARGET_DOMAIN=

# API Keys (optional)
API_KEY=

# PostgreSQL
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=recon_kg
PG_USER=postgres

# Output
OUTPUT_DIR=./tooling/output

LOG_LEVEL=info
```
