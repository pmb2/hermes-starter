#!/usr/bin/env bash
# =============================================================================
# Hermes Starter Kit — One-Command Setup
# =============================================================================
# Installs config, skills, scripts, plugins, prompts, templates, profiles
# into your Hermes home. Idempotent — safe to re-run.
#
# Usage: bash scripts/setup.sh
# =============================================================================
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/AppData/Local/hermes}"
[ -d "$HOME/.hermes" ] && [ ! -d "$HOME/AppData/Local/hermes" ] && HERMES_HOME="$HOME/.hermes"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Hermes Starter Setup ==="
echo "Hermes home: $HERMES_HOME"
echo "Repo:        $REPO_DIR"
mkdir -p "$HERMES_HOME"
echo ""

# 1. config.yaml — only if not already present
if [ -f "$HERMES_HOME/config.yaml" ]; then
    echo "⏭️  config.yaml already exists — not overwriting (edit it directly)"
else
    if [ -f "$REPO_DIR/config/config.example.yaml" ]; then
        cp "$REPO_DIR/config/config.example.yaml" "$HERMES_HOME/config.yaml"
        echo "✅ Created config.yaml from template — edit model + discord sections"
    fi
fi

# 2. .env — only if not already present
if [ -f "$HERMES_HOME/.env" ]; then
    echo "⏭️  .env already exists — not overwriting"
else
    if [ -f "$REPO_DIR/.env.example" ]; then
        cp "$REPO_DIR/.env.example" "$HERMES_HOME/.env"
        echo "✅ Created .env from template — add your API keys"
    fi
fi

# 3. skills
if [ -d "$REPO_DIR/skills" ]; then
    mkdir -p "$HERMES_HOME/skills"
    n=0
    for skill_root in "$REPO_DIR/skills/"*/; do
        [ -d "$skill_root" ] || continue
        cat_name=$(basename "$skill_root")
        for skill_dir in "$skill_root"*/; do
            [ -d "$skill_dir" ] || continue
            skill_name=$(basename "$skill_dir")
            if [ -d "$HERMES_HOME/skills/$cat_name/$skill_name" ]; then
                echo "⏭️  skill $cat_name/$skill_name exists"
            else
                mkdir -p "$HERMES_HOME/skills/$cat_name"
                cp -r "$skill_dir" "$HERMES_HOME/skills/$cat_name/$skill_name"
                n=$((n+1))
            fi
        done
    done
    echo "✅ Skills copied ($n new)"
fi

# 4. scripts (cron jobs + watchdogs resolve from here)
if [ -d "$REPO_DIR/scripts" ]; then
    mkdir -p "$HERMES_HOME/scripts"
    for f in "$REPO_DIR/scripts/"*; do
        [ -f "$f" ] || continue
        cp -n "$f" "$HERMES_HOME/scripts/" || true
    done
    echo "✅ Scripts copied (no overwrites)"
fi

# 5. plugins
if [ -d "$REPO_DIR/plugins" ]; then
    mkdir -p "$HERMES_HOME/plugins"
    for p in "$REPO_DIR/plugins/"*/; do
        [ -d "$p" ] || continue
        name=$(basename "$p")
        [ -d "$HERMES_HOME/plugins/$name" ] || cp -r "$p" "$HERMES_HOME/plugins/$name"
    done
    echo "✅ Plugins copied"
fi

# 6. prompts + templates
for d in prompts templates; do
    if [ -d "$REPO_DIR/$d" ]; then
        mkdir -p "$HERMES_HOME/$d"
        for f in "$REPO_DIR/$d/"*; do
            [ -f "$f" ] || continue
            cp -n "$f" "$HERMES_HOME/$d/" || true
        done
    fi
done
echo "✅ Prompts + templates copied"

# 7. profiles (example personas)
if [ -d "$REPO_DIR/profiles" ]; then
    mkdir -p "$HERMES_HOME/profiles"
    for p in "$REPO_DIR/profiles/"*/; do
        [ -d "$p" ] || continue
        name=$(basename "$p")
        [ -d "$HERMES_HOME/profiles/$name" ] || cp -r "$p" "$HERMES_HOME/profiles/$name"
    done
    echo "✅ Example profiles copied"
fi

echo ""
echo "=== Setup complete ==="
echo "Next:"
echo "  1. Edit $HERMES_HOME/.env      — add your API keys + Discord bot token"
echo "  2. Edit $HERMES_HOME/config.yaml — set model + discord channel IDs"
echo "  3. hermes doctor"
echo "  4. hermes gateway run        (after Discord bot is invited)"
echo "Full guide: https://github.com/pmb2/hermes-starter/blob/main/BOOTSTRAP.md"