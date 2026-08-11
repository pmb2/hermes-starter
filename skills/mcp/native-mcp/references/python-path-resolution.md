# Python Path Resolution in MCP Projects

When a Python MCP server or connector script lives in a subdirectory of a multi-module project, relative path resolution using `__file__` is a common source of bugs.

## The `os.path.dirname(__file__)` Depth Trap

Scripts nested several levels deep (e.g., `app/connectors/yt_archive.py`) use `os.path.dirname(os.path.abspath(__file__))` to reach the project root. Each `dirname()` call climbs one directory level.

```python
# At app/connectors/yt_archive.py:
# dirname(__file__)         → app/connectors/
# dirname(dirname(...))     → app/              ← WRONG for project-root files
# dirname(dirname(dirname(...))) → project-root/ ← CORRECT
```

**Rule of thumb:** you need one `dirname()` per directory level from the script to the root. A script at `app/connectors/foo.py` needs three: `os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`.

## Detecting the Bug

**The dry-run tell.** If a script has a `--dry-run` mode that reports "Already processed: 0" (or any count you know is wrong), the script is likely reading the wrong database file or looking in the wrong directory.

Compare file sizes — two copies of the same file at different levels is a strong red flag:
```
app/pim.db      → 0 bytes     (stale — script was reading this one)
pim.db          → 44.5 MB     (live — should be reading this one)
```

**The stale-copy hazard.** When a project has multiple copies of the same data file at different directory depths, the `__file__`-based path usually resolves to the wrong one — the nearest match to the script's location, which may be a 0-byte stale artifact.

## Verification

After fixing the `dirname()` depth, verify with:
1. Syntax check: `python -c "import ast; ast.parse(open('script.py').read())"`
2. Dry run: confirm "Already processed" count now matches the live database
3. Full test suite: `pytest -x -q` (if available)

## Relation to MCP Workdir Limits

The `native-mcp` skill documents that MCP stdio servers have **no `workdir`/`cwd` configuration option**. Servers must `os.chdir()` to their project root on startup. The same constraint applies to support scripts invoked from within MCP project trees — they cannot rely on the shell cwd being correct, so `__file__`-relative resolution is the standard pattern, making correct `dirname()` depth essential.

## References

- `native-mcp` SKILL.md → "No workdir/cwd support" pitfall
- `native-mcp` SKILL.md → "Python MCP server won't start" troubleshooting
