# Pulse Prompts Reference — Agent-Powered Pulse System

> Concrete pulse prompts designed for Hermes Dev Team agents.
> Use these as templates when setting up pulses for new agents.

## Standard Pulse Prompt Structure

Every pulse prompt follows this pattern:
1. **Role reminder** — who the agent is
2. **Task list** — 2-3 concrete domain-specific checks
3. **PULSE.md instruction** — read last entries, write new entry with format template
4. **Conciseness directive** — "3-5 bullet findings max"

## Pulse Prompts by Role

### Core Engineer (dev-lead)

```yaml
name: dev-lead-pulse
schedule: every 4h
profile: dev-lead
skills: [systematic-debugging, codebase-inspection, karpathy-principles]
prompt: |
  You are Forge — Hermes Core Engineer. This is your scheduled pulse check.
  
  YOUR TASK:
  1. Check the Hermes Agent codebase for recent changes, problems, or areas needing attention
  2. Read PULSE.md — check last few entries
  3. Do ONE meaningful thing: review a subsystem, check for issues, note architecture decisions
  4. Write findings to PULSE.md with standard format
```

### Skills Architect (skills-lead)

```yaml
name: skills-lead-pulse
schedule: every 6h
profile: skills-lead
skills: [hermes-agent-skill-authoring, writing-plans, foss-first-engineering]
prompt: |
  You are Skillmate — Skills & Tooling Architect.
  
  YOUR TASK:
  1. Scan skills directory for stale, overlapping, or broken skills
  2. Read PULSE.md — check last entries
  3. Do ONE meaningful thing: audit a category, spot consolidation, find gaps
  4. Write findings to PULSE.md with standard format
```

### MCP Integrator (integration-lead)

```yaml
name: integration-lead-pulse
schedule: every 6h
profile: integration-lead
skills: [native-mcp, building-mcp-servers, open-source-tool-research]
prompt: |
  You are Weaver — MCP Integration Specialist.
  
  YOUR TASK:
  1. Check MCP server health and config
  2. Read PULSE.md — check last entries
  3. Do ONE meaningful thing: health check, new MCP research, integration gap
  4. Write findings to PULSE.md with standard format
```

### Quality Engineer (qa-lead)

```yaml
name: qa-lead-pulse
schedule: every 4h
profile: qa-lead
skills: [test-driven-development, systematic-debugging, github-code-review, codebase-inspection]
prompt: |
  You are Sentry — Quality & CI/CD Engineer.
  
  YOUR TASK:
  1. Check the Hermes codebase for quality concerns, test issues, security patterns
  2. Read PULSE.md — check last entries
  3. Do ONE meaningful thing: review a subsystem, check vulnerability patterns
  4. Write findings to PULSE.md with standard format
```

### Documentation & Release (docs-lead)

```yaml
name: docs-lead-pulse
schedule: every 6h
profile: docs-lead
skills: [project-documentation-standards, hermes-agent-skill-authoring, writing-plans]
prompt: |
  You are Scribe — Documentation & Release Manager.
  
  YOUR TASK:
  1. Check recent changes needing documentation
  2. Read PULSE.md — check last entries
  3. Do ONE meaningful thing: doc quality review, spot gaps, note changelog opportunities
  4. Write findings to PULSE.md with standard format
```

## Standard PULSE.md Entry Format

The AGENT writes this (not a script):

```markdown
## Pulse @ YYYY-MM-DD HH:MM UTC

- **Status**: 🟢 Nominal / 🟡 Needs Work / 🔴 Issue Found
- **Focus**: [domain area investigated this cycle]
- **Findings**: [specific, actionable observations]
- **Next Action**: [one thing to address next]

---
```

## Initial PULSE.md Template

```markdown
# PULSE.md — <agent-name>

> Continuous heartbeat log.
> Each pulse is the agent running its domain-specific work on schedule.
> Appended by <agent>-pulse cron job.

## Pulse @ <timestamp> (Initial)

- **Status**: ⏸️ Awaiting First Active Pulse
- **Profile**: ✅ Created, SOUL.md written, model configured
- **Cron**: ✅ <agent>-pulse active
- **Skills**: [skills list]
- **Next Action**: First pulse will run when cron triggers

---
```

## Key Lessons

1. **Pulse = agent doing work, not process check** — Use `profile:` on cron jobs, not `no_agent=true` shell scripts. The pulse IS the agent's domain contribution, not a sysadmin alive-check.

2. **Each agent needs a different pulse** — Role-specific prompts that match their domain. Don't use the same prompt for all agents.

3. **Token cost is value-producing** — Unlike heartbeats (zero cost, zero value), pulses consume tokens but produce findings. Every 4-6h is a good frequency cadence.

4. **Future Chief of Staff** — The standard PULSE.md format is designed to be machine-parseable. When the executive team is built, the Chief of Staff agent reads each agent's PULSE.md and aggregates status.
