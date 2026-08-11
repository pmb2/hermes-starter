# Skill Content Deduplication Workflow

When a skill has both inline pitfall sections AND reference files in `references/` with the same content, the duplication wastes space, creates maintenance burden, and risks content divergence.

## Detection

1. **List all reference files**: `ls skills/<category>/<skill>/references/`
2. **Find inline `## Pitfalls:` sections** in `SKILL.md` that overlap with reference filenames
3. **Common overlap signals**:
   - Reference file `platform-guard-autouse-fixture.md` ↔ inline `## Pitfalls: Platform Guard Short-Circuits`
   - Reference file `parent-process-env-leakage.md` ↔ inline `## Pitfalls: Parent-Process Env Var Leakage`
   - Reference file `python-module-identity-split.md` ↔ inline `## Pitfalls: Python Module Identity Split`
4. **Check each for content overlap** — reference files often contain the same worked examples, diagnostic steps, and fix patterns as the inline sections.

## Extraction Process

1. **Read the full inline section** — including the `## Pitfalls:` header, all content, and the blank line before the next section.
2. **Use `patch()`** with:
   - `old_string` = the FULL inline section text
   - `new_string` = `## Pitfalls: <title>\n\nSee \`references/<file>.md\` for <brief description>.\n`
   - `path` = absolute Windows path (`C:/Users/.../SKILL.md`) — MSYS `/c/` paths cause `C:\c\` resolution on Windows
3. **Verify** — re-read the file to confirm the link is in place and the next section starts correctly.

## CRLF Handling

- `skill_manage(action='patch')` SILENTLY FAILS on CRLF files (reports success, doesn't modify)
- `patch()` standalone tool (not skill_manage) handles CRLF correctly on Windows
- For CRLF files, ensure `old_string` includes `\r\n` line endings — the literal `\r\n` bytes, not the escape

## Pitfalls

- **Don't delete reference files** — they contain standalone expanded content that's valuable when the user loads the skill in detail
- **Don't leave broken section headers** — the replacement link should be under the SAME `## Pitfalls:` heading so the section structure is preserved
- **Don't forget to verify** — check `wc -c` before and after to confirm the expected byte reduction
