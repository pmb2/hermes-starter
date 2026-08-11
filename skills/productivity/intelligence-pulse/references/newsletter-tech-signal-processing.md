# Newsletter Technology Signal Processing

**Purpose:** Convert technology newsletters (AlphaSignal, TLDR, The Neuron, etc.) from email into actionable tool installs, config changes, and PIM entries.

## Overview

Newsletters like AlphaSignal appear in email inboxes daily with curated lists of new AI tools, papers, repos, and techniques. Without a processing workflow, the user reads them and moves on — the intel never enters the system. This reference covers the end-to-end pipeline:

1. **Detect** — find the newsletter in the inbox
2. **Extract** — read the content and identify tools/libraries/news
3. **Evaluate** — cross-reference against the current stack and priorities
4. **Install** — install relevant tools, add MCP servers, update configs
5. **Persist** — save findings to PIM (memory + gbrain + local file) for future reference

## Data Sources

| Source | IMAP Address | How to Find | Frequency |
|--------|-------------|-------------|-----------|
| **AlphaSignal** | `<your-email>@gmail.com` | Search `FROM alphasignal` | Daily |
| **TLDR AI** | `<your-email>@gmail.com` | Search `FROM tldr` | Daily |
| **Other newsletters** | Both | Scan for known newsletter sender patterns | Per pulse |

**Gmail app passwords** (stored in Himalaya config at `~/.config/himalaya/config.toml`):
- `<your-email>@gmail.com` — `${GMAIL_APP_PASSWORD}`
- `<your-email>@gmail.com` — `ufwdgehdyolxlbkm`

**youraccount2 quota note:** This account is over Google's free 15GB storage quota. IMAP still works for reading messages, but sending/receiving may be limited. Clear storage or buy more space to restore full functionality.

## Workflow

### Step 1: Connect to Inbox

Use either:
- **Himalaya CLI** (when the account is default): `himalaya envelope list from alphasignal --output json`
- **Python IMAP direct** (when CLI flags don't work across subcommands, or for complex extraction):

```python
import imaplib, email
from email.header import decode_header

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("<your-email>@gmail.com", "APP_PASSWORD")
mail.select("INBOX")
status, ids = mail.search(None, 'FROM', 'alphasignal')
# Fetch and process...
mail.logout()
```

### Step 2: Read Newsletter Content

Read the full email body (not just subject line). Newsletters like AlphaSignal embed the full content in the email body — no link-following needed.

Look for these sections in the email:
- **Top News** — major releases and announcements
- **Top Repo** — notable GitHub repositories
- **Signals** — quick-hit items (tools, papers, methods)
- **Sponsored/Partnership content** — less relevant, but may contain useful tools

### Step 3: Extract Actionable Items

For each tool/repo/technology mentioned, run through a FOUR-GATE filter:

**Gate 1: FOSS Check (first, fastest)**
- Is it open source? Check license in repo (MIT, Apache-2.0, AGPL, BSD = pass)
- Is it proprietary? (Claude Code, GPT-5.5, Grok Build, Cursor = remove immediately)
- the operator explicitly filters out non-FOSS. Don't evaluate further if it's proprietary.
- Exception: SaaS platform integrations (Twenty CRM, Discord, etc.) are infrastructure, not tools being recommended.

**Gate 2: Stack Comparison (do we already have something better?)**
- Search memory/skills for existing tools that serve the same purpose
- Ask: "Do we already have this or something that does it better?"
- Check: is the existing tool already deeply integrated (MCP servers, pipelines, configs)?
- If we already have a more capable tool, skip. Document WHY we skipped (what we have instead) for the evaluation trail.
- **Check if already on system** before recommending install. Common known-preinstalled items to check first: cal.diy/cal.com (Docker), vaultwarden (often VPS/remote), faster-whisper (pip), himalaya CLI, Ollama, Docker.

**Gate 3: Full-Stack Improvement Check (best fit wins — NOT project-tied)**

Evaluate against the ENTIRE Hermes ecosystem, NOT just the user's P0 project or current conversation context:
- Does it improve ANY Hermes profile or conversation? (Not just the current project context)
- Does it add a genuinely new capability across the stack?
- Could it be integrated as a shared resource (MCP server, skill, plugin) that multiple profiles benefit from?
- Does it replace a paid tool anywhere in the stack?
- Is it relevant to ongoing research (polymorphic malware, red teaming, AI safety) even if not project-tied?

**CRITICAL: Evaluate for ALL projects, not just the one you're discussing.** the operator explicitly corrected this: non-P0 projects and cross-stack improvements matter. A tool that improves the bizdev agent profile is as valuable as one that improves land sales. A library relevant to red-team/polymorphic research is worth capturing even if no project currently pursues it.

When you find yourself thinking "this doesn't apply to [current project]", stop and ask: "which OTHER project or profile would this improve?" If the answer is still none, then skip.

**Gate 4: Output**
| Outcome | Label | Action |
|---------|-------|--------|
| Passes all gates | ★ IMPLEMENT | Install + configure + save to PIM + document in the relevant skill/reference |
| We have something better | SKIP — already have | Document why and what we have instead. Record in evaluation. |
| Not FOSS | REMOVE | Do not consider further. Note the license. |
| Cross-stack potential | ★ CROSS | Works for multiple profiles. Tag each affected project. |
| Research-relevant | 🔬 NOTE | Relevant to an ongoing research direction (polymorphic, red-teaming, etc.). Save reference, don't install yet. |
| Not relevant anywhere | SKIP | One-line explanation covering whole stack. |

### Step 4: Install & Configure

For each tool selected for install:

1. **Determine install method**: `pip install`, `npm install -g`, `go install`, binary download, docker
2. **Check prerequisites**: Python version, Node version, binary dependencies
3. **Install**: Run the install command with appropriate timeout
4. **For MCP servers**: Add to Hermes config at `~/.hermes/config.yaml` under `mcp_servers:` or via `hermes mcp add`
5. **Verify**: Run a quick smoke test or version check

**Common install patterns:**

| Type | Command | Verification |
|------|---------|-------------|
| Python package | `pip install <name>` | `<name> --version` |
| Node/npm global | `npm install -g <package>` | `<package> --version` |
| NPX MCP server | `npx -y @scope/package` | Add to Hermes MCP config, test with `hermes mcp test <name>` |
| GitHub clone + setup | `git clone <url> && cd <dir> && pip install -e .` | `python -c "import <module>"` |

**Hermes MCP server config format:**

```yaml
mcp_servers:
  my-new-server:
    args:
    - -y
    - '@scope/package@latest'
    command: npx
    timeout: 120
```

### Step 5: Save to PIM

Save findings to all three persistence layers:

1. **Memory** — save via `memory` tool with `target=memory`. Keep entries compact (<200 chars each). Consolidate if near the 2,200 char limit by removing stale entries.

2. **gbrain** — create a page via `mcp_gbrain_put_page` with structured frontmatter (date, source, tags). Include tool names, how they relate to the stack, and installation status.

3. **Local file** — write to `~/AppData/Local/hermes/pim/<topic-date>.md` as a durable offline backup that doesn't depend on gbrain/ollama availability.

### Step 6: Handle Hermes Self-Update

When the newsletter describes new Hermes features (like v0.17.0):

1. Check current version: `hermes --version`
2. Run update: `hermes update`
3. **Windows lock issue**: The running hermes.exe can't be replaced. Update writes a shim and schedules replacement on reboot. After reboot, finish with `hermes update --force` if needed.
4. Verify: restart and check `hermes --version` again.

## Example: Processed AlphaSignal #81705 (June 22, 2026)

**Theme:** "Who controls your AI stack? Nous Research just handed it back to you"
**Email:** `<your-email>@gmail.com`, sent Jun 22 04:23 UTC

### Summary of Items Found (across entire Hermes stack)

| Item | Type | License | Verdict | Notes |
|------|------|---------|---------|-------|
| Hermes Agent v0.17.0 | Release | MIT | Already have | 1 commit behind, blocked by running process. Reboot needed. |
| Blank Slate mode | Feature | MIT | Skip for main profile | Would need to re-enable all tools. Good for locked-down sub-profiles. |
| LOCUS dataset | Dataset | CC-BY-NC-4.0 | ★ Implement | 2.2M US local laws. Created `scripts/locus_query.py` for FL land-relevant queries. |
| playwright-mcp (Microsoft) | MCP Server | Apache-2.0 | ★ Implement | Free browser MCP, replaces Browserbase ($39/mo). Installed. |
| Alien languages tool | GitHub | MIT (sui-lang) | 🔬 Cloned | Sui/Isu structured pseudocode for LLMs. Polymorphic encoding research relevance. |
| Stanford STORM | GitHub | MIT | ★ Install | Research agent (29K★). Installed via `knowledge-storm` pip. |
| Voicebox | GitHub | MIT | Cloned | Local voice studio with MCP (27K★). Needs Docker on GPU box. |
| OmniParse | GitHub | GPL-3.0 | Cloned | File-to-LLM conversion (7.6K★). Linux deps, needs Docker. |
| Crawl4AI | Web tool | Apache-2.0 | Skip | Already have better (Camoufox + web_extract + CDP). |
| OpenADE | GitHub | MIT | Skip | Hermes Agent is the full framework. OpenADE is a single-task loop. |
| Cal.com | SaaS | AGPL-3.0 | Already have | Running as Docker container `agency-stack-agency-calcom-1`. |
| Vaultwarden | Server | AGPL-3.0 | Already have | On VPS (not local). Self-hosted Bitwarden. |

### Pruning Corrections (from this processing session)

the operator corrected the evaluation scope — initial pass evaluated items only for land agent project. This was wrong. The correct approach is to evaluate across ALL Hermes profiles and conversations. Key corrections applied:
- Excluded (non-FOSS): Grok Build, Claude Code features, GPT-5.5, Cursor
- Re-evaluated: Alien languages tool (sui-lang) flagged as 🔬 NOTE for polymorphic malware research. Stanford STORM → Install (research skill). Voicebox → Clone for GPU box.
- Skipped but reconsidered: Vibe-trading -> not relevant to any profile. Openscreen/openshorts -> not useful in stack.
- Future watch: vaultwarden (already have), cal.com (already have).

### Finding Tools When the Newsletter Doesn't Link Them

AlphaSignal "Signals" items often list a tool without a direct URL (e.g., "New open-source tool generates alien languages that GPT and Claude can code in better than English" without a repo link). To find these:

1. **Extract conceptual keywords**: alien languages, GPT/Claude, "code in better than English"
2. **Search GitHub by concept**, not name:
   - `github.com/search?q=language+designed+for+LLM+code+generation`
   - Try Japanese/unicode characters if a project uses non-Latin names (e.g., 粋 for sui-lang)
   - Use the GitHub API: `requests.get("https://api.github.com/search/repositories?q=<query>&sort=stars")`
3. **Check star count from the newsletter's "Likes" counter**: The newsletter's "2,852 Likes" is NOT GitHub stars — it's an internal like/engagement counter. The actual repo may have any star count.
4. **Try known design patterns**: Custom "language for LLMs" tools often follow one of these patterns:
   - Structured pseudocode with deterministic ASTs (like Isu)
   - Transpilers from custom syntax to Python/Wasm
   - Closed-vocabulary DSLs with step-level error repair
5. **Cross-reference against known projects in the same category**: For "LLM-native language", check existing repos like `sui-lang`, `Snow`, `orca-lang` for the closest match.
6. **Document what you found vs what was described** — if the exact tool can't be found, document the closest candidates and their relevance. The user can confirm if it's the right one.

## Tool Reference: AlphaSignal Email Structure

AlphaSignal emails are structured HTML emails with this layout:
- **Header**: "AlphaSignal" branding, subscription links
- **Greeting**: Personalized ("Hey the operator, ...")
- **Theme**: Opening paragraph setting the newsletter's theme
- **Summary**: Read time estimate
- **Top Paper / Top News / Top Repo**: Three main sections with details
- **Signals**: Numbered list of 5-6 quick-hit items
- **Detailed sections**: Full writeups for the top picks
- **Footer**: Unsubscribe, sponsorship info

The most actionable content is in:
- "Top News" — new tools, features, business developments
- "Top Repo" — notable GitHub repos worth exploring
- "Signals" items with specific tool names — often the highest signal-to-noise section

## Pitfalls

- **Himalaya CLI version differences**: The `--account` flag may not exist in all versions. When it doesn't work, fall back to Python IMAP direct or temporarily change the `default` account in the config.
- **Gmail quota blocks**: If the account is over Google storage quota, IMAP still works for reading but some operations may be limited. Clear storage or buy more space.
- **Hermes self-update blocked**: Cannot update while hermes is running on Windows. Plan for a reboot or separate update session.
- **Newsletter content in HTML**: AlphaSignal uses HTML emails. The text-based extraction (from `text/plain` MIME part) usually works. If you only get HTML, extract via `BeautifulSoup` or regex.
- **False positives from sponsored content**: Sponsored sections in newsletters contain paid placements. Evaluate these tools more skeptically — they're paying for placement, not organically featured.
- **Over-installation**: Not every cool tool needs to be installed. Evaluate against ALL active projects and priorities first. Tag each tool with which project or stack-layer it benefits. If a tool genuinely has no home across the entire Hermes ecosystem (no profile benefits, no project needs it, no research direction connects), skip it.
- **Default evaluation scope creep**: When asked to evaluate recommendations, the default tendency is to evaluate against the current conversation's project context. This is WRONG for the operator — always evaluate across the ENTIRE Hermes stack (all profiles, all conversations, all projects, research directions). Explicitly check: "would this improve anything else in the stack?" before concluding "skip."
- **Confusing newsletter likes with GitHub stars**: AlphaSignal shows an internal engagement count (e.g., "2,852 Likes") next to each signal item. This is NOT the same as GitHub stars. Don't filter search results by the newsletter's like count.
