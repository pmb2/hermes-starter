# Installing ComfyUI Custom Nodes Inside Docker

## Problem

Git clone of custom nodes inside the ComfyUI Docker container fails with:

```
fatal: could not read Username for 'https://github.com': No such device or address
```

The container's git has no credential helper configured (no SSH keys, no GCM),
so it tries to prompt for a username interactively — which hangs in a
non-TTY context.

## Workarounds (ranked)

### 1. Python urllib + zipfile (best for automation)

Works even in minimal Docker containers. No extra tools needed:

```python
import urllib.request, zipfile, io, os, shutil

url = "https://github.com/OWNER/REPO/archive/refs/heads/main.zip"
resp = urllib.request.urlopen(url)
z = zipfile.ZipFile(io.BytesIO(resp.read()))
z.extractall("/tmp/extract")
src = "/tmp/extract/REPO-main"
dst = "/workspace/ComfyUI/custom_nodes/REPO"
if os.path.exists(dst):
    shutil.rmtree(dst)
os.rename(src, dst)
shutil.rmtree("/tmp/extract", ignore_errors=True)
```

**Caveat:** Some repos return HTML instead of a ZIP (rate limiting, auth walls).
Check `resp.headers.get('Content-Type')` — should be
`application/zip` or `application/octet-stream`. If it's `text/html`,
the ZIP download failed.

### 2. Disable credential helpers

Sometimes the issue is a misconfigured git credential helper:

```bash
GIT_TERMINAL_PROMPT=0 git clone --depth 1 https://github.com/OWNER/REPO.git
```

If this still fails, Git is refusing the clone entirely (not a credential issue).

### 3. Inject a GitHub token

For private repos or when rate-limited:

```bash
git clone --depth 1 https://USER:TOKEN@github.com/OWNER/REPO.git
```

Or pass via env:
```bash
GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=echo git clone --depth 1 https://github.com/OWNER/REPO.git
```

### 4. Install via ComfyUI-Manager API

If ComfyUI-Manager is installed, use its API:

```bash
# Install via Manager's custom node registry
curl -X POST http://127.0.0.1:8188/manager/custom_node_install \
  -H "Content-Type: application/json" \
  -d '{"node": "repo-name"}'
```

## Verify Installation

```bash
# List custom nodes
ls /workspace/ComfyUI/custom_nodes/

# Check node types loaded (look for new class_type entries)
curl -s http://127.0.0.1:8188/object_info | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Total node types: {len(d)}')
# Check for specific node
search = sys.argv[1] if len(sys.argv) > 1 else ''
matches = [k for k in d if search.lower() in k.lower()]
if matches:
    print(f'Matches for \"{search}\": {matches}')
" 2>/dev/null
```

## Known Good URLs

| Node | Source URL | Notes |
|------|-----------|-------|
| ComfyUI-fal-Connector | `https://github.com/badayvedat/ComfyUI-fal-Connector` | git clone works |
| ComfyUI_InstantID | `https://github.com/cubiq/ComfyUI_InstantID` | git clone works |
| ComfyUI_IPAdapter_plus | `https://github.com/cubiq/ComfyUI_IPAdapter_plus` | git clone works |
| ComfyUI-ReActor | `https://github.com/Gourieff/ComfyUI-ReActor` | ZIP works, git may fail |
| ComfyUI-Detailer | `https://github.com/ltdrdata/ComfyUI-Impact-Pack` | Impact Pack includes detailer |
| WAS Node Suite | `https://github.com/WASasquatch/was-node-suite-comfyui` | git clone works |

## Restart Required

After installing nodes, restart the ComfyUI container for them to take effect:

```bash
docker restart yt-anim-comfyui
```

Verify with:
```bash
curl -s http://127.0.0.1:8188/object_info | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Node types loaded: {len(d)}')
"
```
