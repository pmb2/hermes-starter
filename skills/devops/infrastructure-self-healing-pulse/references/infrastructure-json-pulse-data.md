# infrastructure.json — Aggregated Pulse Data Source

The infrastructure pulse at `~/.hermes/pulses/infrastructure.json` periodically writes a snapshot of all key system metrics to a single JSON file. Other pulses and agents can **read this file** instead of running their own probes, avoiding redundant work and a flurry of CLI calls.

## File Location

```
${USER_HOME}\.hermes\pulses\infrastructure.json
```

## Schema

```json
{
  "timestamp": "2026-06-17T10:30:00Z",
  "containers": {
    "total": 89,
    "running": 89,
    "unhealthy": 0,
    "exited": 0
  },
  "poste_oom_count_24h": 8,
  "poste_memory_limit": "1G",
  "gpu": {
    "model": "RTX 3090",
    "temp_c": 44,
    "util_pct": 4,
    "vram_used_mib": 16321,
    "vram_total_mib": 24576
  },
  "disk_root_used_pct": 59,
  "disk_root_free_gb": 389,
  "host_memory_free_gb": 10,
  "host_memory_total_gb": 66.8,
  "load_avg": 14.03
}
```

## How to Read It

```python
import json
with open("${USER_HOME}/.hermes/pulses/infrastructure.json") as f:
    data = json.load(f)
```

Or in shell:

```bash
cat ~/.hermes/pulses/infrastructure.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Containers: {d['containers']['running']}/{d['containers']['total']} running, GPU: {d['gpu']['temp_c']}°C at {d['gpu']['util_pct']}%, Disk: {d['disk_root_used_pct']}% used\")"
```

## What It Replaces (don't run these yourself — just read the JSON)

| Probe | Equivalent in JSON |
|-------|-------------------|
| `docker ps` | `containers.running`, `containers.total`, `containers.unhealthy` |
| `nvidia-smi` | `gpu.temp_c`, `gpu.util_pct`, `gpu.vram_used_mib`, `gpu.vram_total_mib` |
| `df -h /` | `disk_root_used_pct`, `disk_root_free_gb` |
| `free -m` | `host_memory_free_gb`, `host_memory_total_gb` |
| `uptime` | `load_avg` |

## Caveats

- **Staleness:** The JSON is written at an interval (e.g. every 4h). Always check `timestamp` — if it's >6h old, probe directly instead.
- **Poste OOM count:** This is cumulative over 24h. 8 kills is the normal baseline for the 1G memory limit on the poste container.
- **No container-level detail:** The JSON gives aggregate counts. For per-container memory pressure (e.g. Calcom at 90% of limit), run `docker stats --no-stream` directly.
