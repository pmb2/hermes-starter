# AGENTS.md Discovery Patterns

> Real discovery from a 21-file system-wide AGENTS.md scan (June 2026)

## The Blind Spot

Initial search using `search_files` (ripgrep-backed) found only files in `Documents/` but missed:
- All `AppData/Local/hermes/` files (hermes-agent, hermes-office, chief-of-staff — 9 files)
- `~/.codex/AGENTS.md` (hidden directory)
- Bun cache test fixtures

**Worse: the ENTIRE E: drive** was not searched at all. The user's secondary projects span `${MY_REPOS}\Documents\github\` with 50+ repos and 115+ AGENTS.md files across agent-universe, agent-fleet, osint-framework, solumina-agent, and many more.

Root cause: thinking "home directory" = "all" when the user has multi-drive setups.

## Correct Approach: `find` with Exclusions

**Always scan all drives:**

```bash
# C: drive — primary projects, configs
find /c/Users/USER -maxdepth 8 -name "AGENTS.md" \
  -not -path "*/node_modules/*" \
  -not -path "*/go/pkg/mod/*" \
  -not -path "*/venv/*" \
  -not -path "*/.venv/*" \
  -not -path "*/__pycache__/*" \
  -not -path "*/.git/*" \
  -not -path "*/.bun/*" \
  -not -path "*/Temp/*" \
  -not -path "*/pytest-*/*" \
  2>/dev/null | sort

# E: drive — secondary repos (50+ repos, 115+ AGENTS.md files)
find ${MY_REPOS} -name "AGENTS.md" \
  -not -path "*/node_modules/*" -not -path "*/.git/*" \
  -not -path "*/.opencode/*" -not -path "*n8n/data*" \
  -not -path "*_templates*" 2>/dev/null | sort
```

When Python `os.walk` is needed for batch processing, use native Windows paths:
```python
os.walk("E:\\yourdata\\Documents\\github")  # works
os.walk("${MY_REPOS}/...")                   # returns False in os.path.isdir
```

## Targeted Sweeps (Fallback for Large Filesystems)

```bash
# Hermes config & profiles (AppData — deep paths)
find ~/AppData/Local/hermes -name "AGENTS.md" -not -path "*/node_modules/*" | sort

# Cloned repos
find ~/Documents/github -name "AGENTS.md" -not -path "*/node_modules/*" -not -path "*/.git/*" | sort

# Codex / home directory repos (shallow)
find ~ -maxdepth 1 -name "AGENTS.md" | sort

# Hidden config directories
find ~/.codex -name "AGENTS.md" 2>/dev/null
find ~/.hermes -name "AGENTS.md" 2>/dev/null
find ~/.config -name "AGENTS.md" 2>/dev/null
```

## Categorization Rules

| Path Pattern | Classification | DOX Action |
|---|---|---|
| `C:\Users\USER\Documents\github\*\` | User project repo | Full DOX: framework + child docs + index |
| `C:\Users\USER\mem0-repo\` | Home-dir repo | Full DOX |
| `C:\Users\USER\AppData\Local\hermes\hermes-agent\` | Hermes agent config | Full DOX: framework + subsystem children |
| `C:\Users\USER\AppData\Local\hermes\profiles\*\` | Hermes agent profile | Framework + leaf note (no children) |
| `C:\Users\USER\.codex\` | Codex CLI config | Framework + leaf note |
| `${MY_REPOS}\Documents\github\agent-universe\` | Agent universe (71 files) | Root + DOX on ALL agent files (frontmatter-aware) |
| `${MY_REPOS}\Documents\github\agent-fleet\` | Agent fleet (24 files) | Root + DOX on ALL team files (frontmatter-aware) |
| `${MY_REPOS}\Documents\github\osint-framework\` | OSINT framework (22 files) | Root + DOX on ALL agent/module files |
| `${MY_REPOS}\Documents\github\ghl\` | Docker compose platform | Full DOX on root |
| `${MY_REPOS}\Documents\github\solumina-agent\` | Solumina MCP platform | Full DOX on root |
| `${MY_REPOS}\Documents\github\website-landlord\` | SEO platform | Full DOX on root |
| `${MY_REPOS}\Documents\github\<small-repo>\` | Small project repo | Framework on root only |
| `*/node_modules/*` | Dependency | Skip |
| `*/go/pkg/mod/*` | Go module | Skip |
| `*/.bun/install/cache/*` | Bun cache | Skip |
| `*/Temp/*` | Temp artifacts | Skip |
| `*/pytest-*/` | Test fixtures | Skip |
| `*/.opencode/*` | Auto-gen skills | Skip |
| `*n8n/data*` | Data/config files | Skip |
| `*_templates*` | Template files | Skip |

## Real Example: 21 Files Found

From a June 2026 scan of `${USER_HOME}`:

```
# Hermes Agent (9 files — AppData)
hermes-agent/AGENTS.md                          # Root
hermes-agent/gateway/AGENTS.md                  # Child: gateway subsystem
hermes-agent/plugins/AGENTS.md                  # Child: plugin system
hermes-agent/tools/AGENTS.md                    # Child: tool registry
hermes-agent/ui-tui/AGENTS.md                   # Child: terminal UI
hermes-office/AGENTS.md                         # Root
hermes-office/openmemory/api/AGENTS.md          # Child: API server
hermes-office/openmemory/ui/AGENTS.md           # Child: UI app
profiles/chief-of-staff/AGENTS.md               # Leaf profile

# AgentField (3 files — Documents/github)
agentfield/AGENTS.md                            # Root
agentfield/control-plane/AGENTS.md              # Child: Go control plane
agentfield/sdk/AGENTS.md                        # Child: SDK packages

# Mem0 (5 files — home dir)
mem0-repo/AGENTS.md                             # Root
mem0-repo/mem0/AGENTS.md                        # Child: Python SDK
mem0-repo/mem0-ts/AGENTS.md                     # Child: TypeScript SDK
mem0-repo/cli/AGENTS.md                         # Child: CLI tools
mem0-repo/server/AGENTS.md                      # Child: REST server

# Codex (3 files — Documents/Codex)
codex-root/AGENTS.md                            # Root
codex/tui/src/bottom_pane/AGENTS.md             # Child: TUI state machines
codex/thread-store/src/remote/AGENTS.md         # Child: remote thread store

# Codex CLI (1 file — ~/.codex, hidden dir)
.codex/AGENTS.md                                # Leaf (config)
```

Total: 21 user-facing AGENTS.md files across 6 project roots.
