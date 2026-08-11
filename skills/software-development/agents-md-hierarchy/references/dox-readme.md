# DOX README

> Source: https://github.com/agent0ai/dox (README.md)

## How DOX Works

DOX is a tiny AGENTS.md framework that gives an AI agent precise project context.

The agent keeps a hierarchy of AGENTS.md files as the project changes:

- root AGENTS.md contains project-wide instructions and the top-level index
- child AGENTS.md files contain local instructions for specific areas
- before any edit, the agent walks the docs tree from the root to the area it will touch
- the relevant docs give it exact local guidelines, so it does not edit blindly
- after meaningful changes, it updates the affected AGENTS.md files

The result is simple: traverse the docs, understand the local rules, make precise edits, keep the docs current. Less guessing. Less drift. Less "why did it touch that file?"

## How to Use

1. Copy the contents of [AGENTS.md](https://raw.githubusercontent.com/agent0ai/dox/main/AGENTS.md) into your project's AGENTS.md file.
2. That's it. No installation, no dependencies, no package, no runtime.
3. It works with any AI agent that supports AGENTS.md files (Codex, Claude Code, OpenCode, etc.).
4. For existing projects, tell your agent: `Initialize DOX tree for this project now.` It will create all the child AGENTS.md files and indexes.

## Credits

Created by [Agent Zero](https://www.agent-zero.ai/) — open-source agentic AI framework.
