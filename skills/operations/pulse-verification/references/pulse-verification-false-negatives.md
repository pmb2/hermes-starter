# Pulse Verification: Avoiding False-Negative Verdicts — Worked Example

Full detail for the 2026-08-01 Forge godmode audit. The condensed methodology lives in SKILL.md; this file carries the concrete evidence trail and reusable audit transcript.

## The false negative

A prior pulse (12:20 UTC) reported `/godmode` "non-functional — `scripts/godmode_toggle.py` is MISSING" and recommended "DO NOT commit; complete it or stash." It had checked only the repo `scripts/` dir.

## Why it was wrong

The handler (`gateway/slash_commands.py::_handle_godmode_command`) has a 3-path fallback chain; the prior pulse checked only path #2:

1. `$HERMES_HOME/scripts/godmode_toggle.py` — FIRST path; where the script actually lived (5915B, deployed 06:54 ET; HERMES_HOME is set in gateway processes)
2. `<repo>/scripts/godmode_toggle.py` — the only path checked → "MISSING" verdict
3. `$APPDATA/Local/hermes/scripts/godmode_toggle.py` — latent bug: `APPDATA` = `Roaming`, so this resolves to nonexistent `Roaming\Local\hermes`

Evidence the feature was complete and LIVE:
- `grep -rn "prefill_messages_file" gateway/ agent/ hermes_cli/` → `gateway/run.py:5062-5071` reads the TOP-LEVEL `prefill_messages_file` key (exactly where the script writes it), with `agent.prefill_messages_file` legacy fallback
- `agent/chat_completion_helpers.py:1492-1502` + `conversation_loop.py:304` implement the cached system-prompt rebuild the handler docstring describes
- Live config: `config.yaml:33` held the GODMODE system_prompt; `:1229` held `prefill_messages_file: prefill.json`; prefill.json present
- The next session started with the PREFILL content injected verbatim as the first user message — mechanism demonstrably works end-to-end

Corrected verdict: "functional, 3 defects" — not "incomplete, don't commit."

## Verification steps that caught it (reusable)

1. Read the handler source to enumerate ALL lookup paths (don't guess where files live).
2. Grep the runtime for the config keys the script writes — proves the mechanism, not just the file.
3. Grep the live config for the toggled keys — proves the feature is currently active.
4. State the correction explicitly in PULSE.md so later pulses don't carry the bad verdict forward.

## Defects found (checklist applied)

- **Destructive disable**: `enable()` sets `agent["system_prompt"] = GODMODE_SYSTEM_PROMPT` (docstring claims "appended to Hermes's normal system prompt" — code REPLACES); `disable()` pops the key with no backup → pre-existing custom prompt permanently lost.
- **Status false-positive**: `enabled = bool(agent.get("system_prompt")) and prefill.json exists` — a user's own custom prompt + any prefill.json would report GODMODE ENABLED. Should key off `godmode_state.json` / prompt content.
- **Windows path construction**: `Path(os.environ.get("APPDATA", ...)) / "Local" / "hermes"` in both the handler fallback AND the script's own HERMES_HOME fallback → `Roaming\Local\hermes` (nonexistent). Correct: `LOCALAPPDATA` (which IS Local) or prefer `HERMES_HOME`.
- **Non-atomic config write**: `_save_yaml_safe` = full-file `yaml.safe_dump` rewrite, no temp+rename, no lock vs the running gateway (which also writes config on model switch). Low-probability race.

## Disposition guidance for uncommitted work in conflict zones

When a feature is functional but uncommitted in high-conflict files ahead of an overdue rebase:
- Do NOT commit it (rebase hold — growing the stack right before a large rebase increases conflict surface).
- Prefer `git stash` with a descriptive message so the rebase doesn't trip on a dirty tree in conflict files; pop + re-apply after.
- Flag review defects to the owning agent with concrete fix patterns (backup/restore, status keyed to state, LOCALAPPDATA).

## Grep scoping note

Full-tree `grep -rin <term> .` from the hermes-agent repo root timed out at 60s. Scoped form that works:
```bash
grep -rin "godmode" gateway/ hermes_cli/ agent/ scripts/ 2>/dev/null | grep -iv test | head -20
```
