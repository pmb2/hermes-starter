# Source: github.com/multica-ai/andrej-karpathy-skills

The `karpathy-principles` skill is adapted from the CLAUDE.md file at:
https://github.com/multica-ai/andrej-karpathy-skills

## Credits

- **Author**: Andrej Karpathy (original observations on LLM coding pitfalls)
- **Packaging**: multica-ai (github.com/multica-ai/andrej-karpathy-skills)
- **Stars**: ~154K
- **License**: MIT

## Background

This CLAUDE.md distills Karpathy's observations from his extensive experience with LLM code generation into four behavioral principles. It went viral (154K stars) because it directly addresses the most common failure modes of LLM coding assistants: over-engineering, unnecessary refactoring, scope creep, and lack of verification.

The four principles work together as a system:
1. **Think Before Coding** — prevents the "start typing and figure it out" failure mode
2. **Simplicity First** — counters the AI tendency to over-abstract and over-engineer
3. **Surgical Changes** — prevents the "I touched 12 unrelated files while fixing one bug" failure mode
4. **Goal-Driven Execution** — ensures work actually completes instead of wandering

## Integration Notes

Adapted into Hermes Agent as a loadable skill under `software-development/`. Trigger keywords: coding, implementation, code-review, refactoring, pull-request, feature-development.

When used, this skill pairs well with:
- `systematic-debugging` — the fix phase benefits from Karpathy's surgical changes principle
- `test-driven-development` — goal-driven execution maps to RED-GREEN-REFACTOR
- `plan` / `writing-plans` — the plan is the "think first" step for complex tasks
