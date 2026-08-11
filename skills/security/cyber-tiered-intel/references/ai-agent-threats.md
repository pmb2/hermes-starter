# AI-Agent-Specific Threats

This document catalogs threats that specifically target AI agents, agent pipelines,
and agent decision surfaces. These are Tier 1 triggers because they directly affect
our Hermes agent fleet and red team operations.

## Ghostcommit — Image Prompt Injection for Agent Hijacking

**Discovered:** July 2026 (BleepingComputer)

**What it is:** An attack technique where prompt injection is hidden inside images
(pixel-encoded, steganographic, or metadata-based). When an AI agent processes
the image via vision tools (`browser_vision`, `vision_analyze`, or any vision-capable
model call), the injected prompt hijacks the agent's context and can:

- Extract session tokens, API keys, or credentials from the agent's context window
- Re-route tool calls to attacker-controlled endpoints
- Exfiltrate internal data the agent has access to
- Execute commands on the agent's behalf

**Affected surfaces in our stack:**

| Surface | Risk Level | Detail |
|---------|-----------|--------|
| `browser_vision()` | HIGH | Agent screenshots pages that may contain injected images |
| `vision_analyze()` | HIGH | Agent explicitly analyzes images from untrusted sources |
| Browser snapshots | MEDIUM | Images rendered in browser that get incidentally captured |
| Image downloads | MEDIUM | Agent processing of user-provided or scraped images |
| Web scraping | LOW-MEDIUM | Images on scraped pages processed through vision pipeline |

**Why it's Tier 1:** Directly targets our agent decision surfaces. An attacker
who controls an image our agent processes can gain code execution in the agent's
environment — not theoretical, actively weaponized as of July 2026.

**Red team application:** Weaponize images with prompt injection payloads for
social engineering campaigns targeting other AI agent systems. The `godmode`
skill and `osint-redteam` workflow should integrate this technique as a TTP.

## Agent Supply Chain Poisoning

**Threat class:** Compromised packages, models, or datasets that inject malicious
behavior into the agent's decision pipeline.

**Examples:**
- Compromised npm/PyPI packages that alter agent tool behavior
- Malicious model adapters that exfiltrate prompts to command-and-control
- Poisoned training data in fine-tuned models used by agents
- Fake agent frameworks on GitHub with backdoored dependencies

**Detection:** Monitor `npm audit`, `pip audit`, GitHub dependency graphs for
unexpected changes. The `cyber-intel-scanner` log scanning should flag package
repository compromise announcements (e.g., Injective Labs GitHub compromise).

## Session/Cookie Theft from Agent Processes

**Threat class:** Attackers targeting the stored sessions, cookies, and tokens
that agents use to authenticate to external services.

**Attack vectors:**
- Browser profile theft (agent's browser session data)
- `.env` / credential file extraction via prompt injection
- Clipboard hijacking of API keys
- Memory dump of agent process containing plaintext tokens

**Relevant to:** Our Discord, Telegram, GitHub, and OpenAI-connected agent sessions.
Any credential compromise here cascades to platform-level account takeover.

## Weaponized Model Outputs

**Threat class:** Model-generated content designed to subvert agent decision-making.

**Examples:**
- Model outputs containing hidden command instructions that the agent follows
- Tool call hallucination — model outputs that look like valid tool calls
- Context window overflow — outputs that push the agent past its context limit
- Deliberate misclassification to bypass agent safety checks

## Red Team Feeding

Per the operator's directive (June 2026): Anything that enhances our red teaming or
fraud research capabilities should be captured and used to empower our red teaming
AI agents. This means:

1. **Tier 1 AI-agent threats** should be immediately fed to red team agents
   as new TTPs for their campaigns
2. **Tier 2 AI-agent threats** should be logged as research notes for the
   `osint-redteam` skill to incorporate into its methodology
3. **Tier 3 AI-agent threats** should be monitored but not actioned

This document is a living reference — update when new AI-agent-specific threats
are discovered in night research or morning briefing sweeps.
