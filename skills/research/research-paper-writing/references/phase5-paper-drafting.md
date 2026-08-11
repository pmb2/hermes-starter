# Phase 5: Paper Drafting

> Extracted from `skills/research/research-paper-writing/SKILL.md` as a reference file.
> Referenced from the main skill file to keep it under the 100KB size limit.

## Context Management for Large Projects

A paper project with 50+ experiment files, multiple result directories, and extensive literature notes can easily exceed the agent's context window. Manage this proactively:

**What to load into context per drafting task:**

| Drafting Task | Load Into Context | Do NOT Load |
|---------------|------------------|-------------|
| Writing Introduction | `experiment_log.md`, contribution statement, 5-10 most relevant paper abstracts | Raw result JSONs, full experiment scripts, all literature notes |
| Writing Methods | Experiment configs, pseudocode, architecture description | Raw logs, results from other experiments |
| Writing Results | `experiment_log.md`, result summary tables, figure list | Full analysis scripts, intermediate data |
| Writing Related Work | Organized citation notes, .bib file | Experiment files, raw PDFs |
| Revision pass | Full paper draft, specific reviewer concerns | Everything else |

**Principles:**
- `experiment_log.md` is the primary context bridge — it summarizes everything needed for writing without loading raw data files
- **Load one section's context at a time** when delegating
- **Summarize, don't include raw files.** For a 200-line result JSON, load a 10-line summary table
- **For very large projects**: Create a `context/` directory with pre-compressed summaries (contribution.md, experiment_summary.md, literature_map.md, figure_inventory.md)

## The Narrative Principle

**The single most critical insight**: Your paper is not a collection of experiments — it's a story with one clear contribution supported by evidence.

Every successful ML paper centers on what Neel Nanda calls "the narrative": a short, rigorous, evidence-based technical story with a takeaway readers care about.

**Three Pillars (must be crystal clear by end of introduction):**

| Pillar | Description | Test |
|--------|-------------|------|
| **The What** | 1-3 specific novel claims | Can you state them in one sentence? |
| **The Why** | Rigorous empirical evidence | Do experiments distinguish your hypothesis from alternatives? |
| **The So What** | Why readers should care | Does this connect to a recognized community problem? |

**If you cannot state your contribution in one sentence, you don't yet have a paper.**

## Sources Behind This Guidance

| Source | Key Contribution |
|--------|-----------------|
| **Neel Nanda** (Google DeepMind) | The Narrative Principle, What/Why/So What framework |
| **Sebastian Farquhar** (DeepMind) | 5-sentence abstract formula |
| **Gopen & Swan** | 7 principles of reader expectations |
| **Zachary Lipton** | Word choice, eliminating hedging |
| **Jacob Steinhardt** (UC Berkeley) | Precision, consistent terminology |
| **Ethan Perez** (Anthropic) | Micro-level clarity tips |
| **Andrej Karpathy** | Single contribution focus |

## Time Allocation

Spend approximately **equal time** on each of:
1. The abstract
2. The introduction
3. The figures
4. Everything else combined

**Why?** Most reviewers form judgments before reaching your methods.

## Writing Workflow

```
Paper Writing Checklist:
- [ ] Step 1: Define the one-sentence contribution
- [ ] Step 2: Draft Figure 1 (core idea or most compelling result)
- [ ] Step 3: Draft abstract (5-sentence formula)
- [ ] Step 4: Draft introduction (1-1.5 pages max)
- [ ] Step 5: Draft methods
- [ ] Step 6: Draft experiments & results
- [ ] Step 7: Draft related work
- [ ] Step 8: Draft conclusion & discussion
- [ ] Step 9: Draft limitations (REQUIRED by all venues)
- [ ] Step 10: Plan appendix (proofs, extra experiments, details)
- [ ] Step 11: Complete paper checklist
- [ ] Step 12: Final review
```

## Two-Pass Refinement Pattern

When drafting with an AI agent, use a **two-pass** approach (proven effective in SakanaAI's AI-Scientist pipeline):

**Pass 1 — Write + immediate refine per section:** For each section, write a complete draft, then immediately refine it in the same context. This catches local issues (clarity, flow, completeness) while the section is fresh.

**Pass 2 — Global refinement with full-paper context:** After all sections are drafted, revisit each section with awareness of the complete paper. This catches cross-section issues: redundancy, inconsistent terminology, narrative flow, and gaps.

```
Second-pass refinement prompt (per section):
"Review the [SECTION] in the context of the complete paper.
- Does it fit with the rest of the paper? Are there redundancies with other sections?
- Is terminology consistent with Introduction and Methods?
- Can anything be cut without weakening the message?
- Does the narrative flow from the previous section and into the next?
Make minimal, targeted edits. Do not rewrite from scratch."
```

## LaTeX Error Checklist

Append this checklist to every refinement prompt:

```
LaTeX Quality Checklist (verify after every edit):
- [ ] No unenclosed math symbols ($ signs balanced)
- [ ] Only reference figures/tables that exist (\ref matches \label)
- [ ] No fabricated citations (\cite matches entries in .bib)
- [ ] Every \begin{env} has matching \end{env} (especially figure, table, algorithm)
- [ ] No HTML contamination (</end{figure}> instead of \end{figure})
- [ ] No unescaped underscores outside math mode (use \_ in text)
- [ ] No duplicate \label definitions
- [ ] No duplicate section headers
- [ ] Numbers in text match actual experimental results
- [ ] All figures have captions and labels
- [ ] No overly long lines that cause overfull hbox warnings
```

## Step-by-Step Drafting

### Step 5.0: Title
The title is the single most-read element of the paper. It determines whether anyone clicks through.

**Good titles** state the contribution or finding, highlight a surprising result, or name the method + what it does.
**Bad titles** are too generic, too long (>15 words), or jargon-only.

Rules:
- Include method name for citability
- Include 1-2 keywords reviewers will search for
- Avoid colons unless both halves carry meaning
- Test: would a reviewer know the domain and contribution from the title alone?

### Step 5.1: Abstract (5-Sentence Formula)
From Sebastian Farquhar (DeepMind):
1. What you achieved: "We introduce...", "We prove...", "We demonstrate..."
2. Why this is hard and important
3. How you do it (with specialist keywords for discoverability)
4. What evidence you have
5. Your most remarkable number/result

**Delete** generic openings like "Large language models have achieved remarkable success..."

### Step 5.2: Figure 1
Figure 1 is the second thing most readers look at (after abstract). Draft it before writing the introduction — it forces you to clarify the core idea.

Types: Method diagram (new pipeline), Results teaser (compelling result), Problem illustration (unintuitive problem), Conceptual diagram (abstract contribution).

### Step 5.3: Introduction (1-1.5 pages max)
Must include: Clear problem statement, brief approach overview, 2-4 bullet contribution list (max 1-2 lines each). Methods should start by page 2-3.

### Step 5.4: Methods
Enable reimplementation: conceptual outline or pseudocode, all hyperparameters listed, architectural details sufficient for reproduction. Present final design decisions; ablations go in experiments.

### Step 5.5: Experiments & Results
For each experiment, explicitly state: what claim it supports, how it connects to main contribution, what to observe. Requirements: error bars with methodology, hyperparameter search ranges, compute infrastructure, seed-setting methods.

### Step 5.6: Related Work
Organize methodologically, not paper-by-paper. Cite generously — reviewers likely authored relevant papers.

### Step 5.7: Limitations (REQUIRED)
All major conferences require this. Honesty helps: reviewers are instructed not to penalize honest limitation acknowledgment. Pre-empt criticisms by identifying weaknesses first.

### Step 5.8: Conclusion & Discussion
Conclusion (0.5-1 page): Restate contribution, summarize key findings, implications, future work. Discussion (optional): broader implications, connections to other subfields, honest assessment.

**Do NOT** introduce new results or claims in the conclusion.

### Step 5.9: Appendix Strategy
Appendices are unlimited at all major venues. Structure: proofs & derivations, additional experiments, implementation details, dataset documentation, prompts & templates, human evaluation details, additional figures.

Rules: main paper must be self-contained; never put critical evidence only in the appendix; cross-reference explicitly.

### Step 5.10: Ethics & Broader Impact Statement
Most venues now require this. Components: positive societal impact, potential negative impact, fairness & bias, environmental impact (compute carbon footprint), privacy, LLM disclosure.

Common mistakes: claiming "no negative impacts" (reviewers distrust this), being vague, ignoring compute costs, forgetting LLM disclosure.

### Step 5.11: Datasheets & Model Cards (If Applicable)
For new datasets or model releases: include datasheets (motivation, composition, collection, preprocessing, distribution, maintenance, ethical considerations) and model cards (architecture, intended use, metrics, ethical considerations, limitations).

## Page Budget Management

| Cut Strategy | Saves | Risk |
|-------------|-------|------|
| Move proofs to appendix | 0.5-2 pages | Low |
| Condense related work | 0.5-1 page | Medium |
| Combine tables with subfigures | 0.25-0.5 page | Low |
| Use `\vspace{-Xpt}` sparingly | 0.1-0.3 page | Low if subtle |
| Remove qualitative examples | 0.5-1 page | Medium |
| Reduce figure sizes | 0.25-0.5 page | High |

**Do NOT**: reduce font size, change margins, remove required sections, or use `\small`/`\footnotesize` for main text.

## Writing Style

**Sentence-level clarity (Gopen & Swan's 7 Principles):**
- Subject-verb proximity: Keep subject and verb close
- Stress position: Place emphasis at sentence ends
- Topic position: Put context first, new info after
- Old before new: Familiar info → unfamiliar info
- One unit, one function: Each paragraph makes one point
- Action in verb: Use verbs, not nominalizations
- Context before new: Set stage before presenting

**Word choice (Lipton, Steinhardt):**
- Be specific: "accuracy" not "performance"
- Eliminate hedging: drop "may" unless genuinely uncertain
- Consistent terminology throughout
- Avoid incremental vocabulary: "develop", not "combine"

## LaTeX Templates

**Always copy the entire template directory first, then write within it.**

Template Setup: Copy full template dir → Verify it compiles as-is → Read example content → Replace section by section → Use template macros → Clean up artifacts at the end.

### Quick Template Reference

| Conference | Main File | Page Limit |
|------------|-----------|------------|
| NeurIPS 2025 | `main.tex` | 9 pages |
| ICML 2026 | `example_paper.tex` | 8 pages |
| ICLR 2026 | `iclr2026_conference.tex` | 9 pages |
| ACL 2025 | `acl_latex.tex` | 8 pages |
| AAAI 2026 | `aaai2026-unified-template.tex` | 7 pages |
| COLM 2025 | `colm2025_conference.tex` | 9 pages |

## Tables and Figures

**Tables**: Use `booktabs` for professional formatting. Rules: Bold best value per metric, include direction symbols, right-align numerical columns, consistent decimal precision.

**Figures**: Vector graphics (PDF) for plots, raster (PNG 600 DPI) for photographs. Colorblind-safe palettes (Okabe-Ito or the operator Tol). Verify grayscale readability. Self-contained captions.

## Professional LaTeX Preamble

Add these packages: `microtype` (highest impact for visual quality), `booktabs` (professional tables), `siunitx` (number formatting), `graphicx` (figures), `subcaption` (subfigures), `tikz` (diagrams), `algorithm2e` (pseudocode), `cleveref` (smart references, load AFTER hyperref), `amsmath`/`amssymb`/`mathtools` (math), `xcolor` (colors).

### siunitx Table Alignment
Use the `S` column type for decimal-aligned numbers in tables.

### Pseudocode with algorithm2e
Standard `algorithm` environment with `\KwIn`, `\KwOut`, `\While`, `\For`, `\eIf` keywords.

### TikZ Diagram Patterns
Common ML paper diagrams: Pipeline/Flow diagrams, Comparison/Matrix diagrams, Iterative Loop diagrams. Use `tikzpicture` with defined styles.

### latexdiff for Revision Tracking
```bash
latexdiff paper_v1.tex paper_v2.tex > paper_diff.tex
```
For multi-file: `latexdiff --flatten paper_v1.tex paper_v2.tex > paper_diff.tex`

### SciencePlots for matplotlib
```bash
pip install SciencePlots
```
```python
import scienceplots
with plt.style.context(['science', 'no-latex']):
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
```

Standard figure sizes: Single column `(3.5, 2.5)`, Double column `(7.0, 3.0)`, Square `(3.5, 3.5)`.

## Conference Resubmission

For converting between venues, see the main skill's `references/submission-preparation.md` — it covers the full conversion workflow, page-change table, and post-rejection guidance.
