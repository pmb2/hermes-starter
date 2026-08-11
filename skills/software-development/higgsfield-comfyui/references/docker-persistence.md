# Docker ComfyUI: Custom Node + Dep Persistence

## Problem

Docker containers created with `docker compose up -d` start from a clean
image each time. Custom nodes installed via `git clone` inside the container
and Python packages installed via `pip install` are **lost on every
`docker compose down && docker compose up`**.

This is the default behavior because custom nodes live in
`/workspace/ComfyUI/custom_nodes/` which is inside the container's writable
layer — not a persistent volume.

## Solution: Bootstrap Script in a Mounted Volume

Mount a bootstrap script from the host and call it before starting ComfyUI.

### Step 1: Create bootstrap.sh on the host

Place it in a directory that's already volume-mounted into the container.

For the yt-animations setup, the `./workflows` directory is mounted at
`/workspace/ComfyUI/user/default/workflows`:

```bash
# ${MY_REPOS}/Documents/github/yt-animations/workflows/bootstrap.sh
```

### Step 2: Add pip installs + git clones

```bash
#!/bin/bash
set -euo pipefail

CUSTOM="/workspace/ComfyUI/custom_nodes"

# Python deps (lost on container recreate)
pip install -q insightface fal-client 2>/dev/null || true

# Custom nodes (lost on container recreate)
[ ! -d "$CUSTOM/ComfyUI-fal-Connector" ] && \
  git clone --depth 1 https://github.com/badayvedat/ComfyUI-fal-Connector.git \
    "$CUSTOM/ComfyUI-fal-Connector" 2>/dev/null

[ ! -d "$CUSTOM/ComfyUI_InstantID" ] && \
  git clone --depth 1 https://github.com/cubiq/ComfyUI_InstantID.git \
    "$CUSTOM/ComfyUI_InstantID" 2>/dev/null
```

### Step 3: Add to docker-compose command

Modify the `command:` in docker-compose.yml to call bootstrap.sh before
the ComfyUI server:

```yaml
command: ["bash", "-lc", "set -euo pipefail;
  bash /workspace/ComfyUI/user/default/workflows/bootstrap.sh 2>/dev/null;
  python3 main.py --listen 0.0.0.0 --port 8188 --normalvram"]
```

## What Gets Wiped vs What Persists

| Artifact | Persists? | Why |
|----------|-----------|-----|
| Models (`/workspace/ComfyUI/models/`) | ✅ | Volume `comfyui-models` |
| Outputs (`/workspace/ComfyUI/output/`) | ✅ | Volume `comfyui-output` |
| User config (`/workspace/ComfyUI/user/default/`) | ✅ | Volume `comfyui-user` |
| Workflows (mounted) | ✅ | Host bind `./workflows` |
| **Custom nodes** (`custom_nodes/`) | ❌ | No volume — in container layer |
| **Python deps** (`pip install`) | ❌ | No volume — in container layer |
| **Model cache** (`~/.cache/huggingface/`) | ❌ | Not mounted |

## Env Var Pass-Through

Docker Compose reads env vars from:
1. The shell environment when running `docker compose up`
2. A `.env` file in the **same directory as docker-compose.yml**

Env vars set in `${USER_HOME}\AppData\Local\hermes\.env` are **NOT**
passed to Docker containers. Place them in the compose project's `.env`:

```bash
# ${MY_REPOS}/Documents/github/yt-animations/.env
FAL_KEY=fal-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then wire them in docker-compose.yml:

```yaml
services:
  comfyui:
    ...
    environment:
      FAL_KEY: ${FAL_KEY:-}
      HF_TOKEN: ${HF_TOKEN:-}
```

## Restart Commands

```bash
# Quick restart (keeps pip deps + custom nodes — uses existing container)
docker restart yt-anim-comfyui

# Full recreate (triggers bootstrap — deps + nodes reinstalled)
docker compose down comfyui
docker compose up -d comfyui
```
