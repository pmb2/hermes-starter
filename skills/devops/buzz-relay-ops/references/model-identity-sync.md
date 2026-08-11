# Buzz Model Identity Sync

Cross-reference to `ai-model-router-gateway/references/model-identity-system.md` for the full spec.

## Quick summary

When OmniRoute model changes, Buzz Desktop agent avatars update to show a **colored ring** around the character art. The ring color indicates which model is active. Each model has a short code badge (WH, PWR, DS, etc.) visible in the corner.

## Files involved

| File | Role |
|------|------|
| `model_identity.json` | Fleet model catalog + active model key |
| `model_identity.py` | CLI (`switch`, `override`, `sync-buzz`) + ring SVG generator |
| `managed-agents.json` | Buzz Desktop agent registry — rewritten on sync |

## Sync command

```bash
cd %LOCALAPPDATA%/hermes/scripts
python model_identity.py sync-buzz
```

This rewrites `%APPDATA%/xyz.block.buzz.app/agents/managed-agents.json` — updating `avatar_url`, `model`, `provider`, and `system_prompt` for every non-builtin agent. Restart Buzz Desktop to see changes.

## Per-agent overrides

```bash
python model_identity.py override dev-lead powerful    # Forge gets Powerful ring
python model_identity.py unset-override dev-lead       # Back to fleet default
python model_identity.py overrides                  # List all overrides
```

## Bridge integration

The `buzz_agent_bridge.py` LLM router reads the active model from `model_identity.resolve_for_agent(slug)`, so the bridge honors both fleet-wide switches and per-agent overrides without restart.