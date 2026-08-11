# Geospatial Tracking — Extending Maps for Movement & Checkpoints

## Vision (from the operator, June 2026)

> "If I say I parked the car here, I want you to know where 'here' is. If I got on my roller blades or bike and went on a path for a while — X time and X distance — I want to ask: how far from the car am I? How do I get back to the car? How far have I gone?"

This requires three capabilities the base `maps` skill doesn't have:
1. **Location checkpoints** — store a named location with coordinates
2. **Path/movement tracking** — log waypoints with timestamps along a route
3. **Accumulated distance + return routing** — calculate cumulative trail distance and route back to a checkpoint

## What Maps Already Provides (Foundation)

| Need | Maps Skill Coverage | Gap |
|------|-------------------|-----|
| Geocode "Eiffel Tower" → coordinates | ✅ `search` | — |
| Coordinates → "near the Louvre" | ✅ `reverse` | — |
| Distance between two points | ✅ `distance` (driving/walking/cycling) | Only A→B, not accumulated path |
| Turn-by-turn back to start | ✅ `directions` (needs two known points) | Needs checkpoint as origin |
| Known place → "what's nearby" | ✅ `nearby` | — |
| Timezone at a location | ✅ `timezone` | — |

## What Needs Building

### 1. Checkpoint Memory

A lightweight store (JSON file or SQLite) for named locations:

```json
{
  "car": {"lat": 40.7484, "lon": -73.9856, "note": "Parked near entrance", "timestamp": "2026-06-04T14:30:00Z"},
  "trail_start": {"lat": 40.7500, "lon": -73.9800, "timestamp": "2026-06-04T15:00:00Z"}
}
```

**MCP tool design:**
- `checkpoint_set(name, lat, lon, note?)` — store a location
- `checkpoint_get(name)` — retrieve stored checkpoint
- `checkpoint_list()` — all saved checkpoints
- `checkpoint_clear(name)` — remove one
- `checkpoint_distance(name)` — straight-line + road distance from current position

### 2. Path/Movement Logging

Record waypoints as a path is traveled:

```json
{
  "session_20260604_bike": {
    "start": {"lat": 40.7484, "lon": -73.9856, "time": "14:30:00"},
    "waypoints": [
      {"lat": 40.7490, "lon": -73.9840, "time": "14:32:15"},
      {"lat": 40.7505, "lon": -73.9820, "time": "14:35:00"}
    ]
  }
}
```

**MCP tool design:**
- `track_start(name)` — begin a named tracking session
- `track_waypoint(lat, lon)` — log a point (called every few seconds/minutes)
- `track_end(name)` — close session, save total stats
- `track_status(name)` — current session distance, duration, avg speed

### 3. Accumulated Distance & Return Routing

**Compute cumulative path distance** using Haversine formula (straight-line between consecutive waypoints, summed):

```python
import math
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
```

**Return routing:** Use the existing `maps distance` and `maps directions` commands with checkpoint as origin:

```bash
# "How do I get back to the car?"
python3 ~/.hermes/skills/maps/scripts/maps_client.py distance "<current_lat>,<current_lon>" --to "<checkpoint_lat>,<checkpoint_lon>" --mode walking

# Turn-by-turn
python3 ~/.hermes/skills/maps/scripts/maps_client.py directions "<current_lat>,<current_lon>" --to "<checkpoint_lat>,<checkpoint_lon>" --mode walking
```

## Recommended FOSS Building Blocks

| Tool | Purpose | License | Already Have? |
|------|---------|---------|-------------|
| **OSM Nominatim** | Geocoding | ODbL | ✅ maps skill |
| **OSRM** | Road routing + travel time | BSD-2 | ✅ maps skill |
| **GeoPy** | Python geocoding wrapper (Nominatim, etc.) | MIT | ❌ (optional) |
| **Shapely** | Point-in-polygon, buffer, geometry ops | BSD-3 | ❌ (optional) |
| **Haversine (manual)** | Straight-line distance | Public Domain | ✅ (can compute) |

## How "Here" Gets Set

Hermes needs to know the user's current location. Options:

1. **User tells us:** "I parked at the mall" → `search` → `checkpoint_set("car", result.lat, result.lon)`
2. **Ol' GPS** — small Python server that reads GPSd or serial USB GPS
3. **Browser Geolocation API** — via Firefox MCP: `navigator.geolocation.getCurrentPosition()`
4. **Phone app** — a simple Android/iOS app that POSTs location to an endpoint
5. **GPX import** — user uploads a GPX file from their cycling computer / phone
6. **IP geolocation** — rough, only city-level accuracy

## Implementation Order (Recommended)

1. **Phase 1 — Checkpoint + Query** (pure maps skill extension)
   - `checkpoint_set/get/list` backed by a JSON file
   - "How far from the car?" → checkpoint_get + maps_client.py distance
   - "How to get back?" → checkpoint_get + maps_client.py directions

2. **Phase 2 — Path tracking** (needs GPS input)
   - `track_start/waypoint/end` with waypoint accumulation
   - Cumulative distance via Haversine
   - Can start with manual waypoint entry ("I'm at the bridge now, log it")

3. **Phase 3 — Automated tracking** (needs GPS data source)
   - Phone app or GPS watch integration
   - GPX file parsing
   - Real-time tracking via WebSocket

## Related Files

- `SKILL.md` — Main maps skill with search/reverse/nearby/distance/directions
- `scripts/maps_client.py` — CLI client for OpenStreetMap/OSRM APIs
