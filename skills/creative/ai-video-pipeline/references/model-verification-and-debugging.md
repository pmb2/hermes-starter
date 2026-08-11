# Model Verification & Debugging Recipes

## Verify FLUX checkpoint integrity
```bash
docker exec yt-anim-comfyui python3 -c "
import safetensors.torch as st
ckpt = '/workspace/ComfyUI/models/checkpoints/flux1-schnell-fp8.safetensors'
data = st.load_file(ckpt)
print(f'Keys: {len(data)}')
for k in list(data.keys())[:5]:
    print(f'  {k}: {data[k].shape} {data[k].dtype}')
total = sum(v.numel() * v.element_size() for v in data.values())
print(f'Total weights size: {total/1024**3:.1f} GB')
# Should see 1438 keys, ~16.1GB total weight data
"
```

## Quick ComfyUI FLUX test (from host)
```python
import requests, json
COMFYUI = 'http://127.0.0.1:8188'
wf = json.load(open('workflows/flux_text_to_image.json'))
def render(n, r):
    if isinstance(n, str):
        for k,v in r.items(): n = n.replace(k,v)
        return n
    elif isinstance(n, dict): return {k: render(v,r) for k,v in n.items()}
    elif isinstance(n, list): return [render(v,r) for v in n]
    return n
repl = {
    '{{MODEL_NAME}}': 'flux1-schnell-fp8.safetensors',
    '{{POSITIVE_PROMPT}}': 'MS Paint style, simple flat colors, white background. A cartoon brown seed with green sprout.',
    '{{NEGATIVE_PROMPT}}': 'blurry, low quality, deformed, realistic, 3d',
    '{{WIDTH}}': '1024', '{{HEIGHT}}': '1024',
    '{{SEED}}': '42', '{{STEPS}}': '4', '{{CFG}}': '1.0',
}
wf = render(wf, repl)
resp = requests.post(f'{COMFYUI}/prompt', json={'prompt': wf, 'client_id': 'test'}, timeout=30)
pid = resp.json()['prompt_id']
# Poll history until done, then download output image
```

## Check generated frame quality
```python
from PIL import Image
import numpy as np
img = Image.open('frame.png').convert('RGB')
arr = np.array(img)
unique = len(np.unique(arr.reshape(-1,3), axis=0))
print(f'{unique} unique colors')
# >100 unique colors = likely valid image
# 1 unique color = solid color = generation failed (check CFG=1.0 and VRAM)
```

## Docker volumes for model files
- Models: `yt-animations_comfyui-models` → `/workspace/ComfyUI/models/`
- Output: `yt-animations_comfyui-output` → `/workspace/ComfyUI/output/`
- User: `yt-animations_comfyui-user` → `/workspace/ComfyUI/user/default/`
- Workflows: bind mount from `./workflows` on host

## docker cp is unreliable for >4GB across MSYS/WSL boundary
Use `docker compose up -d --force-recreate comfyui` after config changes instead.

## Duplicate command: in docker-compose.yml
If `docker compose up` fails with "mapping key 'command' already defined",
run `grep -n "command:" docker-compose.yml` to find both occurrences, then
remove the duplicate. The correct command override uses `--normalvram`
(when VRAM is available) or `--lowvram` (under pressure).

## Successful FLUX test (2026-06-10)
After freeing ~14GB VRAM by killing Docker Desktop, Firefox, Edge, OneDrive,
RustDesk, PhoneExperienceHost:
- ComfyUI startup flag: `--normalvram`
- VRAM: 9,936 used / 14,381 free
- FLUX.1-schnell fp8, 1024x1024, 4 steps, CFG=1.0
- Result: valid 1024x1024 PNG, 224KB, 14,491 unique colors
- Generation time: ~39s (includes model load, subsequent frames ~10-15s)
