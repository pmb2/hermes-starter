# Multi-Agent Parallel Pulse Checks

For comprehensive system health diagnostics across all domains simultaneously, run parallel pulse checks via `delegate_task(tasks=[...])`. Each subagent gets domain-specific skills, tools, and a focused scope.

## Pattern

```python
delegate_task(tasks=[
    {
        "goal": "Core engineering pulse",
        "toolsets": ["terminal", "file"],
        "context": "Check Hermes config integrity, gateway process health, error logs, plugin system"
    },
    {
        "goal": "Skills/tooling pulse",
        "toolsets": ["terminal", "file", "search"],
        "context": "Audit skill inventory, name collisions, manifests, cron references, frontmatter"
    },
    {
        "goal": "MCP integration pulse",
        "toolsets": ["terminal", "file", "web"],
        "context": "Probe all MCP server endpoints, check config validity, Firefox/git-stars health"
    },
])
```

## Pulse Domains

| Domain | Toolsets | Typical Checks | Skills |
|--------|----------|----------------|--------|
| **Core Engineering** | terminal, file | Gateway health, config integrity, error logs, plugin state, cron job health | systematic-debugging, codebase-inspection |
| **Skills/Tooling** | terminal, file, search | Skill inventory, name collisions, manifests, cron refs, frontmatter validity | hermes-agent-skill-authoring, foss-first-engineering |
| **MCP Integration** | terminal, file, web | Server health, ports, config validation, Firefox/git-stars, Docker-based MCPs | native-mcp, building-mcp-servers |
| **Quality/CI** | terminal, file, search | Test collection, lint state, credential leaks, CI configs, code quality | tdd, systematic-debugging, github-code-review |
| **Documentation** | terminal, file | Changelog, README accuracy, doc freshness, version tracking, ECOSYSTEM.md accuracy | project-documentation-standards, docs-standards |

## Result Compilation

Each subagent returns a structured summary with problem severity (LOW/MED/HIGH/CRITICAL). The parent agent:

1. Compiles all findings into a unified problem table
2. Applies instant fixes for LOW/HIGH issues that have known playbooks
3. Notes CRITICAL/complex issues for planning
4. Reports the summary

## Real-World Example

In a real session with 5 pulse domains (Forge, Skillmate, Weaver, Sentry, Scribe), the parallel approach discovered:

- **CRITICAL**: Firefox CDP down (blocked git-stars + personal-intelligence MCPs) → auto-fixed
- **CRITICAL**: Gateway state files stale (6 PIDs marked "running" but dead) → auto-cleaned  
- **HIGH**: ECOSYSTEM.md 264% wrong (said 14 profiles, actually 37) → flagged for planning
- **MEDIUM**: 10 skill name/directory mismatches → flagged for planning
- **MEDIUM**: Credential files committed to repo → flagged for planning
- **LOW**: Config backup files stale → auto-cleaned

Total wall time: ~6 minutes for the full 5-domain scan.
