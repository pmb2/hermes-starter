---
name: karpathy-principles
description: "Andrej Karpathy's behavioral guidelines for LLM coding — think first, simplicity, surgical changes, goal-driven execution. Complements systematic-debugging at the mindset level."
version: 1.5.0
author: Hermes Agent (adapted from Andrej Karpathy's talks, tweets, and essays + multica-ai)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [karpathy, coding-principles, best-practices, behavior, guidelines, debugging, mindset]
    triggers: [coding, implementation, code-review, refactoring, debugging, troubleshooting, root-cause, investigation]
    related_skills: [systematic-debugging, test-driven-development]
---

# Karpathy Principles

> Think first. Read the source. Build to understand. Change only when you know.

## Overview

These principles — drawn from Andrej Karpathy's talks, essays, and engineering practice — sit one level above `systematic-debugging`. Where that skill gives you a **process** (the four phases), this one gives you a **mindset**: the habits of thought that make debugging productive and engineering code clean.

**Load this when:** you're about to debug something unfamiliar, you've made two quick guesses without resolution, or you're feeling the urge to change things and see what sticks.

**Load `systematic-debugging` alongside this:** it operationalises these principles into a concrete sequence of steps.

---

## The Principles

### 1. Read the Source, Luke

**"Don't write code you don't understand. Before you fix something, read the code that runs the part you're touching. The answer is almost always visible if you trace the execution path."**

- Before proposing any fix, `read_file` the relevant source files
- Trace the call chain upstream: where does the bad value originate?
- If you can't explain what a function does in one sentence, you haven't read carefully enough
- `search_files` + `read_file` in Phase 1 of `systematic-debugging` are how you execute this

### 2. Think First, Change Later

**"The most productive debugging sessions involve minimal code changes and maximum thought. Random changes waste time and create new bugs."**

- Form a hypothesis *before* you make any change
- The "Iron Law" of `systematic-debugging` (no fixes without root cause investigation) is a direct expression of this principle
- Counter the urge to "just try changing X and see"

### 3. The 80/20 of Debugging

**"80% of the time is understanding the problem. 20% is fixing it. If you're spending less than 80% on understanding, you're moving too fast."**

- Phase 1 (Root Cause Investigation) is the 80%. Don't rush it.
- If you feel like you're "almost there" but keep finding new symptoms you missed — you're still in the 80%
- A fix that takes 2 minutes but required 30 minutes of investigation is a **win**

### 4. Build to Understand

**"Sometimes the best way to understand a complex system is to reimplement a small piece of it. When an abstraction is confusing, rebuild it from scratch at a smaller scale."**

- Use `spike` skill for throwaway experiments
- When a caching layer, serialisation path, or protocol adapter resists understanding, write a focused test or script that isolates it
- The snapshot version rejection test pattern is an example: build a fixture with known-bad state, exercise the code path, observe — now you *know* how the cache behaves

### 5. Layer by Layer

**"Understand one layer of abstraction at a time. Don't try to comprehend the entire stack at once. Trace one data path from entry to exit, then switch layers."**

- Start at the outermost layer (API/UI/gateway) and follow the data inward
- For each function, ask: "What are its inputs? What does it do? What are its outputs?"
- Don't enter a nested function until you understand the caller's intent
- Cache layers, middleware, and interceptors are the most common places where data gets silently modified — trace through them deliberately

### 6. Be a Scientist

**"Debugging is applied science. Form a single falsifiable hypothesis. Design the smallest experiment that can disprove it. Run it. Observe. Update your model."**

- ONE change at a time — "add multiple changes and run tests" is cargo-cult science
- Write down your hypothesis before you test it ("I think X is the root cause because Y")
- If the experiment doesn't disprove your hypothesis, that doesn't mean you're right — design another test

### 7. Simple over Clever

**"The simplest solution that works is always the right one. Clever code is harder to debug, harder to maintain, and harder for the next person (including you, in six months) to understand."**

- After finding root cause, ask: "What is the SIMPLEST change that fixes this?"
- Every extra abstraction, delegation, or indirection in the fix is a liability
- If the fix feels clever, it's probably wrong — re-read it and simplify

### 8. Understand the Full Stack

**"Even if you work at one layer, understanding the layers above and below makes you significantly better at your own. A frontend developer who understands the API layer writes better frontend code."**

- When debugging, ask about adjacent systems: the config, the database, the provider, the transport layer
- In Hermes context: config propagation (config.yaml → env → runtime), credential pooling, MCP server lifecycle, cache layers — these cross-cutting concerns create bugs that no single-layer analysis finds

---

## How These Interact with systematic-debugging

| Karpathy Principle | Maps To | How |
|---|---|---|
| Read the Source | Phase 1 | The primary action of root cause investigation |
| Think First | Phase 1 gate | The reason Phase 1 must complete before Phase 2 |
| 80/20 | Phase 1 checklist | You're done investigating when you know both WHAT and WHY |
| Build to Understand | Phase 1.4 | When evidence is sparse, build a minimal reproduction |
| Layer by Layer | Phase 1.5 | Trace data flow one layer at a time |
| Be a Scientist | Phase 3 | Hypothesis → minimal test → observe pattern |
| Simple over Clever | Phase 4.2 | Fix the root cause, not the symptom |
| Full Stack | Phase 1.4 | Gather evidence at every component boundary |

---

## Pitfalls

- **"Read the source" doesn't mean skim.** If you read the wrong function or miss the key line, you'll form a wrong hypothesis. Read with intent.
- **"Think first" is NOT paralysis by analysis.** If you've formed a clear hypothesis, test it. The principle aims at *random changes*, not at avoiding action.
- **"Simple over clever" is about the fix, not the investigation.** Investigation requires thoroughness. The simplicity comes in the fix.
- **80/20 can feel like wasted time.** It's not. The 80% is the investment; the 20% is the return. Every minute spent understanding saves ten in random-change cycles.

---

## When NOT to Use

- When you already have full understanding and just need to execute — load `subagent-driven-development` instead
- During time-boxed spikes where the goal is exploration, not debugging — load `spike` instead
- When the issue is a missing import, env var, or tool — that's configuration, not debugging

## Reference Files

- `references/python-test-pollution-tracing.md` — concrete debugging pattern for cross-file pytest state pollution from module-level side effects. Covers how to narrow the polluter, find leaked state (env vars, caches, ContextVars), build a reproduction script, and apply the lazy-init fix pattern.
- `references/hermes-test-pollution-lazy-init.md` — case study of the lazy-init pattern applied to Hermes Agent's TestAcpExecAskGate flakiness. Real walkthrough of Read the Source → Be a Scientist → Simple over Clever on a module-level side-effect bug in tools/approval.py. Open this reference when you need a concrete example of the Karpathy principles in a debugging session.
- `references/windows-acp-test-patterns.md` — Windows-specific ACP test failures: CRLF bytes_written inflation from shell pipelines, asyncio ProactorEventLoop pipe incompatibility, and YAML 1.1 `off` boolean quirk in approval config.
- `references/verify-against-upstream.md` — concrete technique for distinguishing pre-existing test failures from regressions by running the failing test against upstream's source. Essential "Be a Scientist" workflow for anyone maintaining a fork with local commits.
- `references/windows-path-home-test-pattern.md` — Windows `Path.home()` ignores `HOME` env var; always patch `USERPROFILE` alongside `HOME` for cross-platform test compatibility.
- `references/windows-realpath-path-trap.md` — Windows `os.path.realpath('/tmp')` resolves to `C:\tmp`, NOT the system temp dir. Fixes path-comparison logic that breaks when Unix-style and Windows-style paths are naively compared.
- `references/source-notes.md` — Attribution and background for the Karpathy principles adaptation (multica-ai source repo).

## Error Recovery

### Symptom: "skill(s) not found and skipped" at session start — name collision with reference file

If `karpathy-principles` is listed as a job requirement but shows "not found" or "skipped" at session start, the cause is almost always a **name collision** between this skill's directory and a reference file of the same name under another skill's `references/` directory.

**Root cause**: `systematic-debugging/references/karpathy-principles.md` (a condensed reference copy) creates an ambiguous match when the loader resolves the name. `skill_view` finds 2 candidates and refuses to pick one.

**Fix**: Rename the offending reference file to a non-colliding name (e.g., `karpathy-mindset.md`):
```bash
skill_manage(action='write_file', name='systematic-debugging',
  file_path='references/karpathy-mindset.md', file_content=...)
skill_manage(action='remove_file', name='systematic-debugging',
  file_path='references/karpathy-principles.md')
```

Verify the collision is resolved: `skill_view(name='karpathy-principles')` should load the full content without an ambiguity warning.

### Symptom: "skill(s) not found and skipped" at session start — full-skill duplicated across directories

If a skill like `systematic-debugging` or `codebase-inspection` shows "not found" at session start and `skill_view` reports:
```
Ambiguous skill name '<name>': 2 skills match across your local skills dir and
external_dirs.
```

**Root cause**: The same skill directory exists in **two** locations — the local Hermes skills dir AND an external config repo (e.g. `hermes-config/skills/`). The resolver finds both and refuses to pick one.

**⚠ Classification constraint**: If the duplicate is a **bundled** skill (shipped with Hermes) or **hub-installed** skill (`hermes skills install`), `skill_manage(action='delete')` will refuse with `"Refusing background curator delete for bundled/hub-installed skill"`. In that case the fix must target the **external-dir copy** instead — remove the overlapping directory from the `external_dirs` location (e.g. `~/Documents/github/hermes-config/skills/<category>/<skill>/`). The user can also stop the `external_dirs` entry from being scanned in `config.yaml`. When a bundled skill conflicts with an external-dir copy, the external-dir copy wins by loader precedence — removing it resolves the collision.

**⚠ Note**: The categorized-path workaround (e.g. `skill_view(name='github/codebase-inspection')`) does NOT resolve this when the duplicate exists in BOTH local AND external dirs at the same categorized path — the resolver still finds 2 matches. Prefer the permanent fix below.

**Permanent fix**: Remove the duplicate from one location. Check which copy is newer, then delete the stale one:
```bash
# Check both copies (example for codebase-inspection)
ls -la ~/.hermes/skills/github/codebase-inspection/SKILL.md
ls -la ~/Documents/github/hermes-config/skills/github/codebase-inspection/SKILL.md
# Delete the stale one
rm -rf <path-to-stale-copy>
```

**Workaround** (when permanent fix isn't feasible): Use the full relative path from the repo root where the two copies are in different category trees:
```bash
skill_view(name='software-development/systematic-debugging')
```
If both copies are at identical categorized paths (e.g. both are `github/codebase-inspection`), only the permanent fix works — neither bare-name nor categorized-path disambiguation helps.

### Symptom: "not found" but "already exists" on create

If `skill_view` says "not found" but `skill_manage create` says "already exists", the YAML frontmatter is likely truncated or malformed. Fix with:
```bash
skill_manage(action='edit', name='karpathy-principles', content=...)
```
Restore valid YAML frontmatter with the correct closing `---`.

### Symptom: "following skill(s) were listed for this job but could not be found and were skipped" — genuinely absent skills

If a cron job or automated session starts by listing required skills that simply **do not exist** anywhere in the library (no collision, no duplication — they're just not installed), the start-of-session message will say:

```
[IMPORTANT: The following skill(s) were listed for this job but could not be found and were skipped: skill-a, skill-b]
```

**Root cause**: The job's metadata or the orchestrator that spawned the session listed these skills as requirements, but no SKILL.md exists for them under any skills directory (local, external, or hub).

**What it means**: This is a **library gap**, not an error in the skill loader. The session runs without those skills — you lose their step-by-step guidance, pitfalls, and reference material. Apply their principles from general knowledge where possible.

**Check what's available**:
```bash
skills_list          # show all installed skills
skill_view(name='<name>')  # try loading the reported skill to confirm absence
```

**Resolution path** (choose one):
1. **Create the missing skill** — `skill_manage(action='create', name='<name>', content='...')` with frontmatter and body covering the class of work the job needs.
2. **Re-install from hub** — if the skill was previously available, try `hermes skills install <name>`.
3. **Remove from job metadata** — if the skill reference is stale (the job references skills that were pruned/consolidated), update the cron job or orchestrator config to drop the reference.
4. **Defer** — if the job runs fine without the skill, log the gap and move on. The session's report can note the missing skill for awareness.

**Detection note**: The start-of-session warning is easy to miss in long sessions. If you hit an unexpected issue during the job, check whether one of the skipped skills would have covered it — that's the symptom that a real gap exists.
