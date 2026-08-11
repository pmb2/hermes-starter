#!/usr/bin/env python3
"""
Dynamic Upstream Merger (DUM) — Smart fork sync tool.

Preserves customizations while merging upstream updates.
Handles content conflicts, modify/delete, and add/add conflicts.

Usage:
  python merger.py init <repo-path> [upstream-url]
  python merger.py sync <repo-path> [--strategy smart|keep-ours|keep-theirs]
  python merger.py resolve <repo-path> [--interactive]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


def run_git(repo_path: str, args: list[str], check=True) -> subprocess.CompletedProcess:
    """Run a git command in the repo directory."""
    return subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=check,
    )


def get_merge_conflicts(repo_path: str) -> list[str]:
    """Get list of files with merge conflicts."""
    result = run_git(repo_path, ["diff", "--name-only", "--diff-filter=U"], check=False)
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def get_unmerged_files(repo_path: str) -> list[dict]:
    """Get detailed info about all unmerged files including conflict type."""
    result = run_git(repo_path, ["status", "--porcelain=v1", "--untracked-files=no"], check=False)
    unmerged = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        # First two chars are status code
        status = line[:2]
        filepath = line[3:].strip()
        if status[0] in "UD" or status[1] in "UDA":
            unmerged.append({"file": filepath, "status": status})
    return unmerged


def is_modified_delete_conflict(repo_path: str, filepath: str) -> bool:
    """Check if a conflict is a modify/delete conflict."""
    result = run_git(repo_path, ["ls-files", "--unmerged", "--", filepath], check=False)
    stages = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            stage = parts[2]
            stages.add(stage)
    # Stages: 1=base, 2=ours, 3=theirs
    # If one side is missing a stage, it's modify/delete
    if "2" not in stages or "3" not in stages:
        return True
    return False


def has_add_add_conflict(repo_path: str, filepath: str) -> bool:
    """Check if both sides added the same file."""
    result = run_git(repo_path, ["ls-files", "--unmerged", "--", filepath], check=False)
    # If both sides added and it conflicted
    if result.stdout.strip():
        return True
    return False


def load_customizations(repo_path: str) -> dict:
    """Load or create the customizations manifest."""
    manifest_path = Path(repo_path) / ".hermes" / "merger-customizations.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {"custom_changes": {}, "custom_added_files": [], "custom_removed_files": [], "last_upstream_base": None}


def save_customizations(repo_path: str, data: dict):
    """Save the customizations manifest."""
    manifest_path = Path(repo_path) / ".hermes" / "merger-customizations.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(data, f, indent=2)


def get_upstream_name(repo_path: str) -> str:
    """Get the name of the upstream remote."""
    result = run_git(repo_path, ["remote", "-v"], check=False)
    for line in result.stdout.splitlines():
        if "upstream" in line and "(fetch)" in line:
            return "upstream"
    return None


def analyze_customizations(repo_path: str, upstream_ref: str) -> dict:
    """Analyze what customizations exist vs upstream base."""
    customizations = {"custom_changes": {}, "custom_added_files": [], "custom_removed_files": []}

    # Get files changed in our branch vs upstream
    result = run_git(repo_path, ["diff", f"{upstream_ref}..HEAD", "--name-status"], check=False)
    if result.returncode != 0:
        print(f"  Warning: Could not diff against {upstream_ref}")
        return customizations

    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status = parts[0]
        filepath = parts[1]

        if status.startswith("A"):
            customizations["custom_added_files"].append(filepath)
        elif status.startswith("D"):
            customizations["custom_removed_files"].append(filepath)
        elif status.startswith("M"):
            customizations["custom_changes"][filepath] = {
                "reason": "custom modification",
                "strategy": "merge-upstream-additions",
                "priority": "medium",
            }

    return customizations


def extract_our_changes(repo_path: str, filepath: str, base_ref: str) -> str:
    """Extract the diff of our changes vs the upstream base for a file."""
    result = run_git(repo_path, ["diff", base_ref, "HEAD", "--", filepath], check=False)
    return result.stdout


def resolve_content_conflict(repo_path: str, filepath: str, strategy: str) -> bool:
    """
    Resolve a content conflict using the given strategy.
    Returns True if resolved, False if needs manual attention.
    """
    if strategy == "keep-ours":
        run_git(repo_path, ["checkout", "--ours", "--", filepath], check=False)
        run_git(repo_path, ["add", filepath], check=False)
        print(f"  ✓ {filepath} — kept our version (strategy: keep-ours)")
        return True

    elif strategy == "keep-theirs":
        run_git(repo_path, ["checkout", "--theirs", "--", filepath], check=False)
        run_git(repo_path, ["add", filepath], check=False)
        print(f"  ✓ {filepath} — took upstream version (strategy: keep-theirs)")
        return True

    elif strategy.startswith("merge"):
        # Smart merge: try to combine both sides
        return smart_merge_file(repo_path, filepath)

    return False


def smart_merge_file(repo_path: str, filepath: str) -> bool:
    """
    Attempt a smart merge of a conflicted file.
    Uses heuristics to determine which parts to keep from each side.
    """
    # Read the conflicted file
    full_path = Path(repo_path) / filepath
    if not full_path.exists():
        # File was deleted in our branch but modified in upstream
        # If it's a customization we need, restore our version
        customizations = load_customizations(repo_path)
        if filepath in customizations.get("custom_removed_files", []):
            # We intentionally deleted it — keep it deleted
            run_git(repo_path, ["rm", filepath], check=False)
            print(f"  ✓ {filepath} — kept deleted (we intentionally removed this)")
            return True
        else:
            # Take upstream's version
            run_git(repo_path, ["checkout", "--theirs", "--", filepath], check=False)
            run_git(repo_path, ["add", filepath], check=False)
            print(f"  ✓ {filepath} — took upstream version (we don't customize this)")
            return True

    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file — use theirs
        run_git(repo_path, ["checkout", "--theirs", "--", filepath], check=False)
        run_git(repo_path, ["add", filepath], check=False)
        print(f"  ✓ {filepath} — took upstream version (binary file)")
        return True

    conflict_markers = re.findall(
        r'<<<<<<< .*?\n(.*?)=======\n(.*?)>>>>>>> .*?\n',
        content,
        re.DOTALL,
    )

    if not conflict_markers:
        # No standard conflict markers — check if it's a modify/delete
        if is_modified_delete_conflict(repo_path, filepath):
            customizations = load_customizations(repo_path)
            if filepath in customizations.get("custom_removed_files", []):
                run_git(repo_path, ["rm", filepath], check=False)
                print(f"  ✓ {filepath} — kept deleted (intentional removal)")
            else:
                run_git(repo_path, ["checkout", "--theirs", "--", filepath], check=False)
                run_git(repo_path, ["add", filepath], check=False)
                print(f"  ✓ {filepath} — took upstream version (not in our manifest)")
            return True
        else:
            print(f"  ? {filepath} — has conflict but no standard markers")
            return False

    # For each conflict region, decide which side to keep
    new_content = content
    for idx, (ours, theirs) in enumerate(conflict_markers):
        ours = ours.strip()
        theirs = theirs.strip()

        # Heuristics:
        # 1. If our change is small and theirs is large — likely upstream refactored, take theirs
        # 2. If our change is adding functionality and they only changed imports — keep ours
        # 3. If both are substantial — try to keep both

        our_lines = ours.split("\n")
        their_lines = theirs.split("\n")

        # Check if our change is primarily import renames
        our_import_changes = sum(1 for l in our_lines if "use " in l or "use crate" in l or "use codex_" in l)
        their_import_changes = sum(1 for l in their_lines if "use " in l or "use crate" in l or "use codex_" in l)

        # Rule: If our side is mostly import changes and theirs is more, they likely refactored
        if our_import_changes > 0 and their_import_changes > our_import_changes:
            # Take theirs for the import section but keep non-import customizations
            decision = "theirs"
        # Rule: If we're the only ones with functional changes
        elif len(our_lines) > len(their_lines) * 1.5 and our_import_changes < len(our_lines) * 0.3:
            # Our change has substantial non-import modifications — keep ours
            decision = "ours"
        # Rule: Upstream changes are small (bug fixes, minor refactors) — take theirs
        elif len(their_lines) <= 3 and len(their_lines) < len(our_lines) * 0.3:
            decision = "theirs"
        # Rule: Added functionality on both sides — merge both
        elif their_import_changes == 0 and our_import_changes == 0:
            decision = "ours"  # Keep ours, report for review
        else:
            # Default: check ratio
            if len(our_lines) < len(their_lines):
                decision = "theirs"
            else:
                decision = "ours"

        # Apply the decision
        if decision == "ours":
            # Replace entire conflict region with our version
            old_marker = f"<<<<<<< ours\n{ours}\n=======\n{theirs}\n>>>>>>> theirs"
            # Also try with different marker labels
            for pattern in [
                f"<<<<<<< HEAD\n{ours}\n=======\n{theirs}\n>>>>>>>",
                f"<<<<<<< ours\n{ours}\n=======\n{theirs}\n>>>>>>> theirs",
                f"<<<<<<< .*?\n{ours}\n=======\n{theirs}\n>>>>>>> .*?",
            ]:
                if pattern in new_content:
                    new_content = new_content.replace(pattern, ours)
                    break
            print(f"  → {filepath} conflict #{idx+1}: kept OUR change ({len(our_lines)} lines)")
        else:
            for pattern in [
                f"<<<<<<< HEAD\n{ours}\n=======\n{theirs}\n>>>>>>>",
                f"<<<<<<< ours\n{ours}\n=======\n{theirs}\n>>>>>>> theirs",
            ]:
                if pattern in new_content:
                    new_content = new_content.replace(pattern, theirs)
                    break
            print(f"  → {filepath} conflict #{idx+1}: took UPSTREAM change ({len(their_lines)} lines)")

    # Write resolved file
    # Remove any remaining conflict markers (fallback regex)
    new_content = re.sub(
        r'<<<<<<< .*?\n.*?=======\n.*?>>>>>>> .*?\n',
        '',
        new_content,
        flags=re.DOTALL,
        count=1,
    )

    full_path.write_text(new_content, encoding="utf-8")
    run_git(repo_path, ["add", filepath], check=False)
    print(f"  ✓ {filepath} — smart merged ({len(conflict_markers)} conflict(s))")
    return True


def generate_llm_prompt(repo_path: str, filepath: str, base_ref: str) -> str:
    """Generate a prompt about the conflict for an LLM to resolve."""
    our_diff = extract_our_changes(repo_path, filepath, base_ref)
    full_path = Path(repo_path) / filepath

    prompt = f"""I need to resolve a git merge conflict in `{filepath}`.

This is a forked repo where we have custom modifications. The conflict is between:
- OURS: Our fork's version (which has custom changes)
- THEIRS: The upstream version (which has new changes from the original project)

## Our customization purpose
[The script should insert the customization reason from the manifest here]

## Our changes (diff vs upstream base)
```diff
{our_diff[:2000]}
```

## Current conflict state
```
{full_path.read_text(encoding="utf-8")[:3000] if full_path.exists() else "(file was deleted)"}
```

## Instructions
For each conflict marker in the file, decide:
1. If our change is custom functionality we added — keep ours
2. If upstream improved/refactored the same area — take theirs (unless it breaks our customization)
3. If both sides added different things — merge both

Respond with a JSON array of decisions:
```json
[{"region": 1, "decision": "ours|theirs|merge", "reason": "..."}]
```
"""
    return prompt


def resolve_modify_delete(repo_path: str, filepath: str) -> bool:
    """Resolve a modify/delete conflict."""
    customizations = load_customizations(repo_path)

    # The file was deleted on one side but modified on the other
    # Check if the file exists on disk (ours preserved it)
    full_path = Path(repo_path) / filepath

    if not full_path.exists():
        # Our side deleted it — check if it's intentional
        if filepath in customizations.get("custom_removed_files", []):
            # We meant to delete this — good
            run_git(repo_path, ["rm", filepath], check=False)
            print(f"  ✓ {filepath} — kept deleted (in our custom removals)")
            return True
        else:
            # Upstream deleted it — take theirs
            run_git(repo_path, ["rm", filepath], check=False)
            print(f"  ✓ {filepath} — accepted upstream deletion")
            return True
    else:
        # Our side kept it, upstream deleted it
        if filepath in customizations.get("custom_changes", {}):
            # We customized this — keep it
            run_git(repo_path, ["add", filepath], check=False)
            print(f"  ✓ {filepath} — kept our customized version (upstream deleted it)")
            return True
        else:
            # We didn't customize — accept upstream deletion
            run_git(repo_path, ["rm", filepath], check=False)
            print(f"  ✓ {filepath} — accepted upstream deletion (not in our manifest)")
            return True


def cmd_init(args):
    """Initialize: set up upstream remote and generate customization manifest."""
    repo_path = args.repo
    upstream_url = args.upstream

    if not Path(repo_path).exists():
        print(f"Error: Repo path {repo_path} does not exist")
        return 1

    # Ensure it's a git repo
    result = run_git(repo_path, ["rev-parse", "--git-dir"], check=False)
    if result.returncode != 0:
        print(f"Error: {repo_path} is not a git repository")
        return 1

    # Add upstream remote if provided
    if upstream_url:
        existing = get_upstream_name(repo_path)
        if existing:
            run_git(repo_path, ["remote", "set-url", "upstream", upstream_url], check=False)
            print(f"  Updated upstream remote -> {upstream_url}")
        else:
            run_git(repo_path, ["remote", "add", "upstream", upstream_url], check=False)
            print(f"  Added upstream remote -> {upstream_url}")

    # Fetch upstream
    result = run_git(repo_path, ["fetch", "upstream"], check=False)
    if result.returncode != 0:
        print(f"Warning: Could not fetch upstream")
        # Try common branch names
        for branch in ["main", "master", "develop"]:
            result = run_git(repo_path, ["rev-parse", f"upstream/{branch}"], check=False)
            if result.returncode == 0:
                upstream_ref = f"upstream/{branch}"
                break
        else:
            print("Error: Could not find upstream branch")
            return 1
    else:
        # Determine upstream default branch
        result = run_git(repo_path, ["remote", "show", "upstream"], check=False)
        if result.returncode == 0:
            # Try to find HEAD branch
            remote_head = run_git(repo_path, ["symbolic-ref", "refs/remotes/upstream/HEAD"], check=False)
            if remote_head.returncode == 0:
                upstream_ref = remote_head.stdout.strip()
            else:
                upstream_ref = "upstream/main"
        else:
            upstream_ref = "upstream/main"

    print(f"  Using upstream ref: {upstream_ref}")

    # Analyze customizations
    print(f"\n  Analyzing customizations vs {upstream_ref}...")
    customizations = analyze_customizations(repo_path, upstream_ref)

    changes_count = len(customizations["custom_changes"])
    added_count = len(customizations["custom_added_files"])
    removed_count = len(customizations["custom_removed_files"])
    total = changes_count + added_count + removed_count

    print(f"  Found {total} customization(s):")
    print(f"    {changes_count} modified file(s)")
    print(f"    {added_count} added file(s)")
    print(f"    {removed_count} removed file(s)")

    # Get upstream base commit
    base_result = run_git(repo_path, ["merge-base", "HEAD", upstream_ref], check=False)
    if base_result.returncode == 0:
        customizations["last_upstream_base"] = base_result.stdout.strip()
        customizations["upstream_ref"] = upstream_ref
        print(f"  Upstream base: {base_result.stdout.strip()[:12]}")

    # Auto-detect reasons for changes based on diff content
    for filepath in list(customizations["custom_changes"].keys()):
        diff = extract_our_changes(repo_path, filepath, upstream_ref)
        if "openrouter" in diff.lower() or "open_router" in diff.lower():
            customizations["custom_changes"][filepath]["reason"] = "OpenRouter support"
        elif "model_provider" in diff.lower() or "provider" in diff.lower():
            customizations["custom_changes"][filepath]["reason"] = "Model provider selection"
        elif "preprompt" in diff.lower():
            customizations["custom_changes"][filepath]["reason"] = "Custom preprompt system"
        elif "import" in diff.lower() and "codex_" in diff:
            customizations["custom_changes"][filepath]["reason"] = "Import path changes for fork compatibility"
        elif "SetServiceTier" in diff or "SetModelProvider" in diff:
            customizations["custom_changes"][filepath]["reason"] = "Replaced SetServiceTier with SetModelProvider"
            customizations["custom_changes"][filepath]["priority"] = "high"
        elif "crate::config" in diff:
            customizations["custom_changes"][filepath]["reason"] = "Fork-specific crate path adjustments"
        elif ".github/workflows/pmb2" in filepath:
            customizations["custom_changes"][filepath]["reason"] = "Custom CI pipeline"
            customizations["custom_changes"][filepath]["priority"] = "high"

    save_customizations(repo_path, customizations)
    print(f"\n  ✅ Customization manifest saved to .hermes/merger-customizations.json")
    print(f"  📝 Review and edit the manifest to add 'reason' for each customization")
    return 0


def try_merge(repo_path: str, upstream_ref: str, strategy: str) -> Optional[int]:
    """Attempt a merge with upstream, returning 0 on success, None if merge failed."""
    # Check for merge conflicts first
    result = run_git(repo_path, ["merge", upstream_ref], check=False)
    if result.returncode == 0:
        return 0

    # Conflicts detected — resolve them
    conflicts = get_merge_conflicts(repo_path)
    customizations = load_customizations(repo_path)

    print(f"  Found {len(conflicts)} conflicted file(s)")

    resolved = 0
    for conflict in conflicts:
        print(f"\n  Processing: {conflict}")

        if is_modified_delete_conflict(repo_path, conflict):
            print(f"    Type: modify/delete")
            if resolve_modify_delete(repo_path, conflict):
                resolved += 1
            continue

        if conflict in customizations.get("custom_changes", {}):
            info = customizations["custom_changes"][conflict]
            reason = info.get("reason", "unknown")
            prio = info.get("priority", "medium")
            print(f"    Customized file — reason: {reason} (priority: {prio})")
            # For high-priority custom files, always keep ours
            if prio == "high":
                run_git(repo_path, ["checkout", "--ours", "--", conflict], check=False)
                run_git(repo_path, ["add", conflict], check=False)
                print(f"    ✓ Kept our version (high-priority customization)")
                resolved += 1
                continue
            if resolve_content_conflict(repo_path, conflict, "keep-ours"):
                resolved += 1
                continue
        elif conflict in customizations.get("custom_added_files", []):
            run_git(repo_path, ["checkout", "--ours", "--", conflict], check=False)
            run_git(repo_path, ["add", conflict], check=False)
            print(f"    ✓ Kept our added file")
            resolved += 1
        else:
            # Not customized — take upstream
            if resolve_content_conflict(repo_path, conflict, "keep-theirs"):
                resolved += 1

    remaining = get_merge_conflicts(repo_path)
    if remaining:
        print(f"\n  ⚠️  {len(remaining)} file(s) still have conflicts:")
        for f in remaining:
            print(f"    - {f}")
        return None

    # Commit the merge
    # Check if there's anything to commit
    status = run_git(repo_path, ["status", "--porcelain"], check=False)
    if status.stdout.strip():
        # Git auto-stages resolved files during merge
        # A merge commit may already be in progress
        merge_head = run_git(repo_path, ["rev-parse", "MERGE_HEAD"], check=False)
        if merge_head.returncode == 0:
            # Let git complete the merge
            run_git(repo_path, ["commit", "--no-edit"], check=False)
            print(f"\n  ✅ Merge commit created")
        else:
            print(f"\n  ✅ All changes applied (no merge commit needed)")
    else:
        print(f"\n  Already up to date (nothing to merge)")
    return 0


def cmd_sync(args):
    """Sync fork with upstream: fetch, rebase or merge, and smart-resolve conflicts."""
    repo_path = args.repo
    strategy = args.strategy
    sync_method = args.method

    if not Path(repo_path).exists():
        print(f"Error: Repo path {repo_path} does not exist")
        return 1

    # Load customization manifest
    customizations = load_customizations(repo_path)

    # Get upstream reference
    upstream_ref = customizations.get("upstream_ref")
    if not upstream_ref:
        upstream_ref = get_upstream_name(repo_path)
        if not upstream_ref:
            print("Error: No upstream remote configured. Run 'init' first.")
            return 1
        upstream_ref = f"upstream/main"

    # Fetch upstream
    print(f"  Fetching upstream...")
    run_git(repo_path, ["fetch", "upstream"], check=False)
    print(f"  ✓ Upstream fetched")

    # Check current branch
    branch = run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)
    current_branch = branch.stdout.strip() if branch.returncode == 0 else "main"
    print(f"  Current branch: {current_branch}")

    # Try merge or rebase based on method
    if sync_method == "merge":
        print(f"\n  Merging {upstream_ref} into current branch...")
        merge_result = try_merge(repo_path, upstream_ref, strategy)
        if merge_result == 0:
            print(f"  ✅ Merge complete!")
            # Update manifest
            new_base = run_git(repo_path, ["rev-parse", "HEAD"], check=False)
            if new_base.returncode == 0:
                customizations["last_upstream_base"] = new_base.stdout.strip()
                save_customizations(repo_path, customizations)
            return 0
        elif merge_result is None:
            print(f"\n  ⚠️  Merge has conflicts that need manual resolution")
            return 1
        else:
            return merge_result

    # Try rebase
    print(f"\n  Attempting rebase onto {upstream_ref}...")
    rebase_result = run_git(repo_path, ["rebase", upstream_ref], check=False)

    if rebase_result.returncode == 0:
        print(f"  ✅ Clean rebase — no conflicts!")
        print(f"\n  Changes incorporated from upstream. Ready to push.")
        return 0

    # Conflicts detected
    print(f"  ⚠️  Rebase produced conflicts. Resolving...")
    conflicts = get_merge_conflicts(repo_path)
    unmerged = get_unmerged_files(repo_path)

    print(f"\n  Found {len(conflicts)} conflicted file(s)")

    # Resolve each conflict
    resolved_count = 0
    manual_count = 0

    for conflict in conflicts:
        print(f"\n  Processing: {conflict}")

        # Determine conflict type
        if is_modified_delete_conflict(repo_path, conflict):
            print(f"    Type: modify/delete")
            if resolve_modify_delete(repo_path, conflict):
                resolved_count += 1
            else:
                manual_count += 1
            continue

        # Content conflict — check customization status
        if conflict in customizations.get("custom_changes", {}):
            custom_strategy = customizations["custom_changes"][conflict].get("strategy", strategy)
            custom_priority = customizations["custom_changes"][conflict].get("priority", "medium")
            custom_reason = customizations["custom_changes"][conflict].get("reason", "unknown")
            print(f"    Customized file — reason: {custom_reason} (priority: {custom_priority})")

            if resolve_content_conflict(repo_path, conflict, custom_strategy):
                resolved_count += 1
            else:
                manual_count += 1
        elif conflict in customizations.get("custom_added_files", []):
            print(f"    Our added file — keeping our version")
            run_git(repo_path, ["checkout", "--ours", "--", conflict], check=False)
            run_git(repo_path, ["add", conflict], check=False)
            resolved_count += 1
        else:
            # Not a customized file — take upstream
            print(f"    Not in customization manifest — taking upstream version")
            if resolve_content_conflict(repo_path, conflict, "keep-theirs"):
                resolved_count += 1
            else:
                manual_count += 1

    # Check for any remaining unmerged files
    remaining = get_merge_conflicts(repo_path)
    if remaining:
        print(f"\n  {'='*50}")
        print(f"  ⚠️  {len(remaining)} file(s) still have conflicts (manual resolution needed):")
        for f in remaining:
            print(f"    - {f}")
        manual_count += len(remaining)

    # Try to continue the rebase
    if manual_count == 0:
        result = run_git(repo_path, ["rebase", "--skip"], check=False)
        if result.returncode != 0:
            result = run_git(repo_path, ["rebase", "--continue"], check=False)
        
        if result.returncode == 0 or "No rebase in progress" in result.stderr:
            print(f"\n  ✅ All conflicts resolved! Rebase complete.")
            print(f"  Push with: git push origin {current_branch} --force-with-lease")
            return 0

        # Check if there are more conflicts in subsequent commits
        more_conflicts = get_merge_conflicts(repo_path)
        if more_conflicts:
            print(f"\n  📦 Additional conflicts found in remaining rebase steps:")
            for f in more_conflicts:
                print(f"    - {f}")
            print(f"\n  Run 'sync' again to resolve the next batch, or use 'resolve'.")
            return 1
    else:
        print(f"\n  {'='*50}")
        print(f"  ⚠️  {manual_count} conflict(s) need manual resolution.")
        print(f"  Run 'resolve --interactive' to step through them, or resolve manually.")
        print(f"\n  After resolving: git rebase --continue")
        return 1

    return 0


def cmd_resolve(args):
    """Step through remaining conflicts interactively."""
    repo_path = args.repo
    interactive = args.interactive

    conflicts = get_merge_conflicts(repo_path)
    if not conflicts:
        print("  No remaining conflicts!")
        return 0

    print(f"  {len(conflicts)} conflict(s) remaining\n")

    for i, conflict in enumerate(conflicts, 1):
        print(f"  [{i}/{len(conflicts)}] {conflict}")
        print(f"  {'─'*50}")

        full_path = Path(repo_path) / conflict
        if full_path.exists():
            with open(full_path) as f:
                content = f.read()
            # Show just the conflict regions
            sections = re.findall(
                r'<<<<<<< .*?\n(.*?)=======\n(.*?)>>>>>>> .*?\n',
                content,
                re.DOTALL,
            )
            for j, (ours, theirs) in enumerate(sections, 1):
                our_lines = ours.strip().split("\n")
                their_lines = theirs.strip().split("\n")
                print(f"\n    Conflict #{j}:")
                print(f"    OURS ({len(our_lines)} lines): {our_lines[0][:80]}...")
                print(f"    THEIRS ({len(their_lines)} lines): {their_lines[0][:80]}...")

        if interactive:
            print(f"\n    Options: [1] keep ours  [2] theirs  [3] edit  [s] skip")
            choice = input(f"    Choice: ").strip()
            if choice == "1":
                run_git(repo_path, ["checkout", "--ours", "--", conflict])
                run_git(repo_path, ["add", conflict])
                print(f"    ✓ Kept ours")
            elif choice == "2":
                run_git(repo_path, ["checkout", "--theirs", "--", conflict])
                run_git(repo_path, ["add", conflict])
                print(f"    ✓ Took theirs")
            elif choice == "3":
                print(f"    Opening editor for {conflict}...")
                # Just print the full conflict for manual resolution
                if full_path.exists():
                    print(f"    Full file at: {full_path}")
                print(f"    After editing: git add {conflict} && git rebase --continue")
                return 1
            else:
                print(f"    Skipped")
        else:
            print(f"\n    Auto-resolving with default strategy...")
            if resolve_content_conflict(repo_path, conflict, "merge"):
                print(f"    ✓ Resolved")

    # Final check
    remaining = get_merge_conflicts(repo_path)
    if remaining:
        print(f"\n  ⚠️  {len(remaining)} conflict(s) still remaining")
        return 1
    else:
        print(f"\n  ✅ All conflicts resolved!")
        result = run_git(repo_path, ["rebase", "--continue"], check=False)
        if result.returncode == 0 or "No rebase in progress" in result.stderr:
            print(f"  Rebase complete. Ready to push.")
        return 0


def cmd_status(args):
    """Show current customization and sync status."""
    repo_path = args.repo

    customizations = load_customizations(repo_path)
    if not customizations or not any([customizations.get("custom_changes"),
                                       customizations.get("custom_added_files"),
                                       customizations.get("custom_removed_files")]):
        print("  No customization manifest found. Run 'init' first.")
        return 1

    print(f"\n  📋 Customization Summary:")
    print(f"  {'='*50}")

    changes = customizations.get("custom_changes", {})
    added = customizations.get("custom_added_files", [])
    removed = customizations.get("custom_removed_files", [])

    if changes:
        print(f"\n  Modified files ({len(changes)}):")
        for f, meta in sorted(changes.items()):
            reason = meta.get("reason", "unknown")
            priority = meta.get("priority", "medium")
            prio_icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            print(f"    {prio_icon} {f}")
            print(f"       Reason: {reason}")

    if added:
        print(f"\n  Added files ({len(added)}):")
        for f in added:
            print(f"    ➕ {f}")

    if removed:
        print(f"\n  Removed files ({len(removed)}):")
        for f in removed:
            print(f"    ➖ {f}")

    base = customizations.get("last_upstream_base", "unknown")
    print(f"\n  Upstream base: {base[:12] if len(base) > 12 else base}")
    
    # Check how far behind upstream we are
    upstream_ref = customizations.get("upstream_ref", "upstream/main")
    behind = run_git(repo_path, ["rev-list", "--count", f"HEAD..{upstream_ref}"], check=False)
    ahead = run_git(repo_path, ["rev-list", "--count", f"{upstream_ref}..HEAD"], check=False)
    if behind.returncode == 0:
        print(f"  Behind upstream: {behind.stdout.strip()} commit(s)")
    if ahead.returncode == 0:
        print(f"  Ahead of upstream: {ahead.stdout.strip()} commit(s)")

    return 0


def generate_codex_manifest(repo_path: str):
    """Auto-generate an optimal customization manifest for the codex fork."""
    customizations = {
        "custom_changes": {},
        "custom_added_files": [],
        "custom_removed_files": [],
        "upstream_ref": "upstream/main",
    }

    # Known codex customizations
    changes = {
        "codex-rs/core/src/config/edit.rs": {
            "reason": "Replaced codex_config imports with crate::config, SetServiceTier with SetModelProvider",
            "strategy": "merge-upstream-additions",
            "priority": "high",
        },
        "codex-rs/tui/src/app.rs": {
            "reason": "Added model provider routing, OpenRouter support. Upstream refactored imports significantly.",
            "strategy": "merge-upstream-additions",
            "priority": "high",
        },
        "codex-rs/tui/src/app_event.rs": {
            "reason": "Replaced many unused imports with OpenRouter-compatible types",
            "strategy": "keep-ours",
            "priority": "high",
        },
        "codex-rs/tui/src/chatwidget.rs": {
            "reason": "Added OpenRouter model support, model provider display. Upstream refactored imports heavily.",
            "strategy": "merge-upstream-additions",
            "priority": "high",
        },
        "codex-rs/tui/src/slash_command.rs": {
            "reason": "Customized slash commands for pmb2 workflow (removed unused commands, added Approvals)",
            "strategy": "keep-ours",
            "priority": "high",
        },
        "codex-rs/core/src/codex.rs": {
            "reason": "Added OpenRouter preprompt injection",
            "strategy": "merge-upstream-additions",
            "priority": "high",
        },
        ".github/workflows/pmb2-sync-publish.yml": {
            "reason": "Custom CI pipeline for pmb2 fork",
            "strategy": "keep-ours",
            "priority": "high",
        },
        "docs/pmb2-private-release.md": {
            "reason": "Documentation for pmb2 private release process",
            "strategy": "keep-ours",
            "priority": "medium",
        },
    }

    # Files we add that upstream doesn't have
    added_files = [
        "codex-rs/core/openrouter_codex_preprompt.md",
        ".github/workflows/pmb2-sync-publish.yml",
        "docs/pmb2-private-release.md",
    ]

    # Files upstream has that we removed or that conflict
    removed_files = []

    customizations["custom_changes"] = changes
    customizations["custom_added_files"] = added_files
    customizations["custom_removed_files"] = removed_files

    # Get base commit
    result = run_git(repo_path, ["merge-base", "HEAD", "upstream/main"], check=False)
    if result.returncode == 0:
        customizations["last_upstream_base"] = result.stdout.strip()

    return customizations


def main():
    parser = argparse.ArgumentParser(description="Dynamic Upstream Merger (DUM)")
    parser.add_argument("--version", action="version", version="DUM v1.0.0")
    parser.add_argument("repo", nargs="?", default=".", help="Path to the git repository")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Init
    init_p = subparsers.add_parser("init", help="Initialize customization manifest")
    init_p.add_argument("--upstream", "-u", help="Upstream repository URL")
    init_p.add_argument("--codex", action="store_true", help="Generate codex-optimized manifest")

    # Sync
    sync_p = subparsers.add_parser("sync", help="Sync with upstream (fetch + merge/rebase + resolve)")
    sync_p.add_argument("--strategy", choices=["smart", "keep-ours", "keep-theirs"],
                        default="smart", help="Resolution strategy")
    sync_p.add_argument("--method", choices=["merge", "rebase"],
                        default="merge", help="Sync method (merge preserves history, rebase replays changes)")

    # Resolve
    res_p = subparsers.add_parser("resolve", help="Resolve remaining conflicts")
    res_p.add_argument("--interactive", "-i", action="store_true", help="Step through conflicts manually")

    # Status
    subparsers.add_parser("status", help="Show customization status")

    args = parser.parse_args()

    if args.command in ("init",):
        if args.codex:
            repo_path = args.repo if args.repo else "."
            customizations = generate_codex_manifest(repo_path)
            save_customizations(repo_path, customizations)
            print(f"  ✅ Codex-optimized customization manifest generated!")
            print(f"  📍 Saved to {Path(repo_path).resolve()}/.hermes/merger-customizations.json")
            return 0
        # Check for upstream in args
        upstream = getattr(args, 'upstream', None)
        return cmd_init(args)

    elif args.command == "sync":
        return cmd_sync(args)

    elif args.command == "resolve":
        return cmd_resolve(args)

    elif args.command == "status":
        return cmd_status(args)

    elif args.command is None:
        parser.print_help()
        return 0

    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
