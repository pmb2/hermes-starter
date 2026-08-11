# CI Integration: GitHub Actions Upstream Sync

This reference shows how to integrate the Dynamic Upstream Merger directly into a GitHub Actions workflow without needing the `merger.py` script. The customization manifest is embedded using `python -c` JSON writing, and the conflict resolver uses a simple `git checkout --ours` / `git checkout --theirs` loop.

## Full Workflow Example (codex pmb2-sync-publish)

```yaml
name: pmb2-sync-publish

on:
  workflow_dispatch:
  schedule:
    - cron: "15 5 * * *"

jobs:
  sync-upstream:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Configure git
        run: |
          git config user.name "pmb2-bot"
          git config user.email "pmb2-bot@users.noreply.github.com"

      - name: Add upstream
        run: |
          git remote add upstream https://github.com/openai/codex.git
          git fetch upstream

      - name: Write customization manifest
        run: |
          mkdir -p .hermes
          python -c "
import json
manifest = {
  'custom_changes': {
    'codex-rs/core/src/config/edit.rs': {'reason': 'OpenRouter: SetServiceTier to SetModelProvider', 'strategy': 'keep-ours', 'priority': 'high'},
    'codex-rs/tui/src/app.rs': {'reason': 'OpenRouter model provider routing', 'strategy': 'keep-ours', 'priority': 'high'},
    'codex-rs/tui/src/chatwidget.rs': {'reason': 'OpenRouter model switching & display', 'strategy': 'keep-ours', 'priority': 'high'},
    'codex-rs/tui/src/slash_command.rs': {'reason': 'Custom pmb2 slash commands', 'strategy': 'keep-ours', 'priority': 'high'},
    'codex-rs/core/src/codex.rs': {'reason': 'OpenRouter preprompt injection', 'strategy': 'keep-ours', 'priority': 'high'},
    '.github/workflows/pmb2-sync-publish.yml': {'reason': 'pmb2 CI pipeline', 'strategy': 'keep-ours', 'priority': 'high'},
    'docs/pmb2-private-release.md': {'reason': 'pmb2 release docs', 'strategy': 'keep-ours', 'priority': 'medium'}
  },
  'custom_added_files': ['codex-rs/core/openrouter_codex_preprompt.md', '.github/workflows/pmb2-sync-publish.yml', 'docs/pmb2-private-release.md'],
  'upstream_ref': 'upstream/main',
  'sync_method': 'merge'
}
with open('.hermes/merger-customizations.json', 'w') as f:
    json.dump(manifest, f, indent=2)
"

      - name: Merge upstream changes (with smart conflict resolution)
        run: |
          git checkout main
          git merge upstream/main 2>&1 || {
            echo "Conflicts detected. Auto-resolving..."
            for file in $(git diff --name-only --diff-filter=U); do
              if python -c "
import json
with open('.hermes/merger-customizations.json') as f:
    m = json.load(f)
if '$file' in m.get('custom_changes', {}) or '$file' in m.get('custom_added_files', []):
    exit(0)
exit(1)
"; then
                echo "  Keeping our version: $file (customized)"
                git checkout --ours -- "$file"
              else
                echo "  Taking upstream version: $file (not customized)"
                git checkout --theirs -- "$file"
              fi
              git add "$file"
            done
            git commit --no-edit
            echo "Auto-merge completed"
          }

      - name: Push merged main
        run: |
          git push origin HEAD:main
```

## Key Design Decisions

1. **Use `python -c` not heredocs for JSON**: YAML breaks on heredocs with JSON content. `python -c` with a triple-quoted string works reliably and avoids YAML indentation issues.

2. **`git merge` not `git rebase`**: Merge creates a merge commit. If a conflict resolution goes wrong, a simple `git revert` of the merge commit fixes everything. With rebase, custom commits can be lost permanently during conflict resolution.

3. **Modify/delete handling is automatic**: When one side deleted a file and the other modified it:
   - If the file exists on disk (our version), `--ours` preserves it
   - If the file doesn't exist (upstream deleted it), `--ours` errors and `--theirs` would restore it
   The loop handles this correctly because customized files always exist on disk and get the `keep-ours` treatment.

4. **No LLM fallback in CI**: The CI version uses a binary keep-ours/keep-theirs decision per the manifest. For complex merges where both sides should be combined, use the `merger.py` script locally with its smart-merge heuristics.
