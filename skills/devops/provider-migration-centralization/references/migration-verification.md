# Migration Verification Script

Run after any provider migration to catch missed references.

```python
import json, pathlib, importlib.util, sys

H = pathlib.Path.home()
errors = []
passes = []

# 1. Central model config loads correctly
sys.path.insert(0, str(H / 'AppData/Local/hermes/scripts'))
from hermes_model import get_config, get_api_key, active_profile, list_profiles

m = get_config()
assert m['provider'] == 'deepseek', f"provider={m['provider']}"
assert m['base_url'] == 'https://api.deepseek.com/v1', f"url={m['base_url']}"
assert m['model'] == 'deepseek-v4-flash', f"model={m['model']}"
passes.append(f"model_config.json: {m['provider']}/{m['model']}")

# 2. API key loads
key = get_api_key()
assert key, "No API key found"
passes.append(f"API key: loaded ({len(key)} chars)")

# 3. No old pinned providers in cron jobs
cj = json.loads((H / 'AppData/Local/hermes/cron/jobs.json').read_text())
jobs = cj.get('jobs', cj) if isinstance(cj, dict) else cj
old_count = sum(1 for j in jobs if isinstance(j, dict) and j.get('provider') == 'opencode-go')
assert old_count == 0, f"{old_count} jobs still pinned to opencode-go"
passes.append("cron/jobs.json: 0 old provider refs")

# 4. Live config points to new provider
uc = (H / '.hermes/config.yaml').read_text()
assert 'provider: deepseek' in uc, ".hermes/config.yaml not updated"
passes.append(".hermes/config.yaml: provider=deepseek")

lc = (H / 'AppData/Local/hermes/config.yaml').read_text()
assert 'provider: deepseek' in lc, "AppData config.yaml not updated"
passes.append("AppData/config.yaml: provider=deepseek")

# 5. Health check passes
spec = importlib.util.spec_from_file_location('cg', str(H / 'AppData/Local/hermes/scripts/cron-guardian.py'))
mod = importlib.util.module_from_spec(spec)
sys.modules['cg'] = mod
spec.loader.exec_module(mod)
healthy, detail, credits = mod.check_model_health()
assert healthy, f"Health FAILED: {detail}"
passes.append(f"Health check: {detail}")

print("=== VERIFICATION PASSED ===")
for p in passes:
    print(f"  ✅ {p}")
```

## Quick Grep Check for Missed References

```bash
# Find any remaining old provider references in scripts
grep -rn 'opencode\.ai|OPENCODE_GO|opencode-go' ~/AppData/Local/hermes/scripts/ --include='*.py' --include='*.sh'

# Find any remaining old provider in cron jobs
grep -c '"provider": "opencode-go"' ~/AppData/Local/hermes/cron/jobs.json
# Should be 0

# Find any remaining old provider in configs
grep -rn 'opencode-go\|opencode\.ai' ~/.hermes/config.yaml ~/AppData/Local/hermes/config.yaml
```
