# Session Recovery Pattern — Annotated Example

**Source session:** 2026-07-12, user the operator (pmb2)
**Recovered thread:** 2026-07-03 FCRA background-check disclosure requests (`20260703_150443_be8496bb`)

## What happened

User opened with:

> "Hows it goin? Keep going! What have we accomplished? What is still left to do? And what are the overall goals?"

I assumed "keep going" referred to the most active project (`website-landlord`) and started reporting build-state, git log, etc.

User corrected:

> "Now, that is incorrect. I just wanted a system update from you. This thread is the thread that we were using. That's pertaining to background checks. I need you to go through our conversations with Hermes agent and find the one where we were talking about the FCRA regulations in the background checks..."

## Recovery steps that worked

1. **Stop the wrong line of reporting immediately.** No further repo/git checks.
2. **Search session history for the topic.** Used `session_search` with queries:
   - `"FCRA background check free file disclosure"`
   - `"background check consumer report dispute"`
3. **Identify the matching session.** Result: `20260703_150443_be8496bb`, July 3, 2026, with multiple "continue"/"keep going" messages.
4. **Read the session in chunks.** Used `session_search(session_id=..., around_message_id=..., window=...)` and a full read to reconstruct:
   - Goal: FCRA Section 609 disclosure requests to 8 vendors
   - Status: all 8 vendors researched, draft saved
   - Stalled on: HireRight form automation / Playwright MCP failures
   - Saved file: `${USER_HOME}\FCRA_Disclosure_Requests_Process_Draft.md`
5. **Verify the artifact on disk.** Read the draft file to confirm contents and last-modified date (2026-07-03 17:28).
6. **Report from the recovered thread.** Gave vendor-by-vendor status, cited the file path, and offered three next-step options.

## Key signals to watch for

- User asks "what have we accomplished" without naming a project.
- User says "keep going"/"continue" after a long gap.
- User corrects with "that is incorrect" and names the real topic.

## Anti-patterns

- Defaulting to the repo in `cwd` or the most recently modified project directory.
- Treating a context-compaction summary as the source of truth.
- Continuing to gather status on the wrong project after the user has already corrected the topic.
