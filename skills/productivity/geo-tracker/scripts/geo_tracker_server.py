"""
Geo Tracker MCP Server — geospatial tracking, checkpoints, geo-fencing, phone location.
Built on OpenStreetMap/OSRM (same engine as the maps skill) with SQLite persistence.
"""
import asyncio, json, math, os, sqlite3, time, threading, urllib.parse, urllib.request
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = os.path.expanduser("~/geo_tracker.db")
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8484
USER_AGENT = "HermesGeo/1.0"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
OSRM_BASE = "https://router.project-osrm.org/route/v1"
OVERPASS_URLS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_db(conn)
    return conn

def _init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            name TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS tracks (
            name TEXT NOT NULL,
            seq INTEGER NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            altitude REAL DEFAULT NULL,
            accuracy REAL DEFAULT NULL,
            speed REAL DEFAULT NULL,
            bearing REAL DEFAULT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (name, seq)
        );
        CREATE TABLE IF NOT EXISTS phone_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            accuracy REAL DEFAULT NULL,
            altitude REAL DEFAULT NULL,
            speed REAL DEFAULT NULL,
            bearing REAL DEFAULT NULL,
            source TEXT DEFAULT 'owntracks',
            ts TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS geo_fences (
            name TEXT PRIMARY KEY,
            center_lat REAL NOT NULL,
            center_lon REAL NOT NULL,
            radius_m REAL NOT NULL DEFAULT 100,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tracks_name ON tracks(name);
        CREATE INDEX IF NOT EXISTS idx_phone_ts ON phone_locations(ts);
    """)
    conn.commit()

# ---------------------------------------------------------------------------
# HTTP helpers (same pattern as maps skill)
# ---------------------------------------------------------------------------
def http_get(url: str, params: dict = None, timeout: int = 15) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

def http_post(url: str, data: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, data=data.encode(), headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())

# ---------------------------------------------------------------------------
# Geospatial math
# ---------------------------------------------------------------------------
def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    p1, p2, dp, dl = math.radians(lat1), math.radians(lat2), math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns bearing in degrees from point 1 to point 2."""
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1)*math.sin(p2) - math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def geocode(query: str, limit: int = 1) -> list:
    """Place name to coordinates via Nominatim."""
    params = {"q": query, "format": "json", "limit": limit, "addressdetails": 1}
    time.sleep(1.0)  # rate limit
    return http_get(NOMINATIM_SEARCH, params=params)

def reverse_geocode(lat: float, lon: float) -> dict:
    """Coordinates to address."""
    params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1}
    time.sleep(1.0)
    return http_get(NOMINATIM_REVERSE, params=params)

def osrm_route(olat: float, olon: float, dlat: float, dlon: float, mode: str = "driving") -> dict:
    """Road distance and duration via OSRM."""
    profiles = {"driving": "driving", "walking": "foot", "cycling": "bicycle"}
    profile = profiles.get(mode, "driving")
    url = f"{OSRM_BASE}/{profile}/{olon},{olat};{dlon},{dlat}?overview=false&steps=true"
    return http_get(url)

def overpass_query(query: str) -> dict:
    for url in OVERPASS_URLS:
        try:
            return http_post(url, "data=" + urllib.parse.quote(query))
        except:
            continue
    return {"error": "All Overpass mirrors failed"}

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("geo-tracker")

# --- Checkpoint Tools ---

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="checkpoint_set", description="Save a named location checkpoint (e.g. 'the car')",
            inputSchema={"type":"object","properties":{"name":{"type":"string","description":"Checkpoint name"},"lat":{"type":"number","description":"Latitude"},"lon":{"type":"number","description":"Longitude"},"description":{"type":"string","description":"Optional description"}},"required":["name","lat","lon"]}),
        types.Tool(name="checkpoint_get", description="Get details for a saved checkpoint",
            inputSchema={"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}),
        types.Tool(name="checkpoint_list", description="List all saved checkpoints",
            inputSchema={"type":"object","properties":{}}),
        types.Tool(name="checkpoint_delete", description="Delete a checkpoint",
            inputSchema={"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}),
        types.Tool(name="track_start", description="Start recording a movement path",
            inputSchema={"type":"object","properties":{"name":{"type":"string","description":"Track name e.g. 'bike-ride-june4'"},"lat":{"type":"number","description":"Starting latitude"},"lon":{"type":"number","description":"Starting longitude"}},"required":["name","lat","lon"]}),
        types.Tool(name="track_point", description="Add a waypoint to an active track",
            inputSchema={"type":"object","properties":{"name":{"type":"string","description":"Track name"},"lat":{"type":"number"},"lon":{"type":"number"},"altitude":{"type":"number"},"accuracy":{"type":"number"},"speed":{"type":"number"},"bearing":{"type":"number"}},"required":["name","lat","lon"]}),
        types.Tool(name="track_end", description="Finish a track and get summary",
            inputSchema={"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}),
        types.Tool(name="track_summary", description="Get track statistics (distance, duration, avg speed) without ending it",
            inputSchema={"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}),
        types.Tool(name="distance_from_checkpoint", description="Get distance and directions from a saved checkpoint to a location",
            inputSchema={"type":"object","properties":{"checkpoint":{"type":"string","description":"Saved checkpoint name"},"to_lat":{"type":"number","description":"Destination latitude"},"to_lon":{"type":"number","description":"Destination longitude"},"mode":{"type":"string","description":"driving/walking/cycling","default":"walking"}},"required":["checkpoint","to_lat","to_lon"]}),
        types.Tool(name="distance_between", description="Road distance and travel time between two places",
            inputSchema={"type":"object","properties":{"from_place":{"type":"string","description":"Origin address or place name"},"to_place":{"type":"string","description":"Destination address or place name"},"mode":{"type":"string","default":"driving"}},"required":["from_place","to_place"]}),
        types.Tool(name="geocode", description="Convert a place name to coordinates",
            inputSchema={"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}),
        types.Tool(name="reverse_geocode", description="Convert coordinates to an address",
            inputSchema={"type":"object","properties":{"lat":{"type":"number"},"lon":{"type":"number"}},"required":["lat","lon"]}),
        types.Tool(name="phone_location_set", description="Record your phone's current GPS location",
            inputSchema={"type":"object","properties":{"lat":{"type":"number"},"lon":{"type":"number"},"accuracy":{"type":"number"},"speed":{"type":"number"},"bearing":{"type":"number"},"source":{"type":"string","default":"manual"}},"required":["lat","lon"]}),
        types.Tool(name="phone_location_get", description="Get the latest known phone location",
            inputSchema={"type":"object","properties":{}}),
        types.Tool(name="phone_location_history", description="Get phone location history",
            inputSchema={"type":"object","properties":{"limit":{"type":"integer","default":20}},"required":[]}),
        types.Tool(name="geo_fence_create", description="Create a circular geo-fence",
            inputSchema={"type":"object","properties":{"name":{"type":"string"},"center_lat":{"type":"number"},"center_lon":{"type":"number"},"radius_m":{"type":"number","default":100}},"required":["name","center_lat","center_lon"]}),
        types.Tool(name="geo_fence_check", description="Check if the phone is inside/outside any geo-fences",
            inputSchema={"type":"object","properties":{}}),
        types.Tool(name="geo_fence_list", description="List all geo-fences",
            inputSchema={"type":"object","properties":{}}),
        types.Tool(name="where_is_my_phone", description="Get the phone's last known location as an address + distance from a checkpoint",
            inputSchema={"type":"object","properties":{"from_checkpoint":{"type":"string","description":"Optional: checkpoint to measure distance from"}},"required":[]}),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    db = get_db()
    try:
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")
        result = handler(db, arguments)
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    finally:
        db.close()

# --- Tool Implementations ---

def _checkpoint_set(db, args):
    db.execute("INSERT OR REPLACE INTO checkpoints (name, lat, lon, description, updated_at) VALUES (?,?,?,?,datetime('now'))",
               (args["name"], args["lat"], args["lon"], args.get("description", "")))
    db.commit()
    return {"status": "ok", "checkpoint": args["name"], "lat": args["lat"], "lon": args["lon"]}

def _checkpoint_get(db, args):
    row = db.execute("SELECT * FROM checkpoints WHERE name=?", (args["name"],)).fetchone()
    if not row:
        return {"error": f"Checkpoint '{args['name']}' not found"}
    addr = reverse_geocode(row["lat"], row["lon"]) if row["lat"] and row["lon"] else {}
    return {"name": row["name"], "lat": row["lat"], "lon": row["lon"],
            "description": row["description"], "address": addr.get("display_name", "Unknown"),
            "created": row["created_at"], "updated": row["updated_at"]}

def _checkpoint_list(db, args):
    rows = db.execute("SELECT name, lat, lon, description, created_at FROM checkpoints ORDER BY name").fetchall()
    return {"checkpoints": [dict(r) for r in rows]}

def _checkpoint_delete(db, args):
    db.execute("DELETE FROM checkpoints WHERE name=?", (args["name"],))
    db.commit()
    return {"status": "deleted", "checkpoint": args["name"]}

def _track_start(db, args):
    name = args["name"]
    lat, lon = args["lat"], args["lon"]
    db.execute("DELETE FROM tracks WHERE name=?", (name,))
    db.execute("INSERT INTO tracks (name, seq, lat, lon, ts) VALUES (?,0,?,?,datetime('now'))", (name, lat, lon))
    db.commit()
    addr = reverse_geocode(lat, lon) if lat and lon else {}
    return {"status": "ok", "track": name, "start": {"lat": lat, "lon": lon, "address": addr.get("display_name", "Unknown")}}

def _track_point(db, args):
    name = args["name"]
    seq_row = db.execute("SELECT COALESCE(MAX(seq), -1) + 1 AS n FROM tracks WHERE name=?", (name,)).fetchone()
    seq = seq_row["n"]
    lat, lon = args["lat"], args["lon"]
    db.execute("INSERT INTO tracks (name, seq, lat, lon, altitude, accuracy, speed, bearing, ts) VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
               (name, seq, lat, lon, args.get("altitude"), args.get("accuracy"), args.get("speed"), args.get("bearing")))
    db.commit()
    # Calculate distance from previous point
    prev = db.execute("SELECT lat, lon FROM tracks WHERE name=? AND seq=?", (name, seq-1)).fetchone()
    dist_from_prev = haversine_m(prev["lat"], prev["lon"], lat, lon) if prev else 0
    return {"status": "ok", "seq": seq, "dist_from_prev_m": round(dist_from_prev, 1)}

def _track_end(db, args):
    name = args["name"]
    points = db.execute("SELECT lat, lon, ts FROM tracks WHERE name=? ORDER BY seq", (name,)).fetchall()
    if len(points) < 2:
        return {"error": "Track needs at least 2 points", "track": name, "points": len(points)}
    total_dist = 0.0
    for i in range(1, len(points)):
        total_dist += haversine_m(points[i-1]["lat"], points[i-1]["lon"], points[i]["lat"], points[i]["lon"])
    start_ts = points[0]["ts"]
    end_ts = points[-1]["ts"]
    try:
        duration_s = (datetime.fromisoformat(end_ts) - datetime.fromisoformat(start_ts)).total_seconds()
    except:
        duration_s = 0
    addr_end = reverse_geocode(points[-1]["lat"], points[-1]["lon"]) if points[-1]["lat"] and points[-1]["lon"] else {}
    return {
        "track": name, "points": len(points),
        "total_distance_m": round(total_dist, 1), "total_distance_km": round(total_dist/1000, 3),
        "duration_seconds": round(duration_s, 1) if duration_s > 0 else "N/A (instant)",
        "duration_minutes": round(duration_s/60, 1) if duration_s > 60 else "N/A",
        "start": {"lat": points[0]["lat"], "lon": points[0]["lon"]},
        "end": {"lat": points[-1]["lat"], "lon": points[-1]["lon"], "address": addr_end.get("display_name", "Unknown")}
    }

def _track_summary(db, args):
    name = args["name"]
    points = db.execute("SELECT lat, lon, ts FROM tracks WHERE name=? ORDER BY seq", (name,)).fetchall()
    if len(points) < 2:
        return {"track": name, "points": len(points), "status": "need at least 2 points for summary"}
    total_dist = sum(haversine_m(points[i-1]["lat"], points[i-1]["lon"], points[i]["lat"], points[i]["lon"]) for i in range(1, len(points)))
    try:
        duration_s = (datetime.fromisoformat(points[-1]["ts"]) - datetime.fromisoformat(points[0]["ts"])).total_seconds()
    except:
        duration_s = 0
    avg_speed_kmh = (total_dist/1000) / (duration_s/3600) if duration_s > 0 else 0
    return {
        "track": name, "points": len(points),
        "total_distance_m": round(total_dist, 1), "total_distance_km": round(total_dist/1000, 3),
        "duration_seconds": round(duration_s, 1) if duration_s > 0 else 0,
        "avg_speed_kmh": round(avg_speed_kmh, 1) if duration_s > 0 else 0
    }

def _distance_from_checkpoint(db, args):
    cp = db.execute("SELECT * FROM checkpoints WHERE name=?", (args["checkpoint"],)).fetchone()
    if not cp:
        return {"error": f"Checkpoint '{args['checkpoint']}' not found"}
    dlat, dlon = args["to_lat"], args["to_lon"]
    mode = args.get("mode", "walking")
    straight_m = haversine_m(cp["lat"], cp["lon"], dlat, dlon)
    brg = bearing(cp["lat"], cp["lon"], dlat, dlon)
    # OSRM route
    route = osrm_route(cp["lat"], cp["lon"], dlat, dlon, mode)
    road_dist = route.get("routes", [{}])[0].get("distance", 0) if route.get("code") == "Ok" else None
    road_time = route.get("routes", [{}])[0].get("duration", 0) if route.get("code") == "Ok" else None
    # Direction name
    dir_names = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    dir_name = dir_names[round(brg / 45) % 8]
    return {
        "from": {"name": cp["name"], "lat": cp["lat"], "lon": cp["lon"]},
        "to": {"lat": dlat, "lon": dlon},
        "straight_line_m": round(straight_m, 1), "straight_line_km": round(straight_m/1000, 3),
        "bearing_deg": round(brg, 1), "direction": dir_name,
        "road_distance_m": round(road_dist, 1) if road_dist else None,
        "road_duration_min": round(road_time/60, 1) if road_time else None,
        "mode": mode
    }

def _distance_between(db, args):
    from_place = args["from_place"]
    to_place = args["to_place"]
    mode = args.get("mode", "driving")
    f = geocode(from_place, 1)
    if not f: return {"error": f"Could not geocode '{from_place}'"}
    t = geocode(to_place, 1)
    if not t: return {"error": f"Could not geocode '{to_place}'"}
    flat, flon = float(f[0]["lat"]), float(f[0]["lon"])
    tlat, tlon = float(t[0]["lat"]), float(t[0]["lon"])
    route = osrm_route(flat, flon, tlat, tlon, mode)
    straight_m = haversine_m(flat, flon, tlat, tlon)
    return {
        "from": {"query": from_place, "display": f[0].get("display_name"), "lat": flat, "lon": flon},
        "to": {"query": to_place, "display": t[0].get("display_name"), "lat": tlat, "lon": tlon},
        "mode": mode,
        "straight_line_km": round(straight_m/1000, 3),
        "road_distance_km": round(route.get("routes",[{}])[0].get("distance",0)/1000, 3) if route.get("code")=="Ok" else None,
        "road_duration_min": round(route.get("routes",[{}])[0].get("duration",0)/60, 1) if route.get("code")=="Ok" else None
    }

def _geocode(db, args):
    results = geocode(args["query"], 5)
    return {"query": args["query"], "results": [{"lat": float(r["lat"]), "lon": float(r["lon"]),
        "display_name": r.get("display_name"), "type": r.get("type")} for r in results]}

def _reverse_geocode(db, args):
    result = reverse_geocode(args["lat"], args["lon"])
    return {"lat": args["lat"], "lon": args["lon"], "address": result.get("display_name", "Unknown"),
            "details": result.get("address", {})}

def _phone_location_set(db, args):
    db.execute("INSERT INTO phone_locations (lat, lon, accuracy, altitude, speed, bearing, source, ts) VALUES (?,?,?,?,?,?,?,datetime('now'))",
               (args["lat"], args["lon"], args.get("accuracy"), args.get("altitude"),
                args.get("speed"), args.get("bearing"), args.get("source", "manual")))
    db.commit()
    return {"status": "ok", "lat": args["lat"], "lon": args["lon"]}

def _phone_location_get(db, args):
    row = db.execute("SELECT * FROM phone_locations ORDER BY ts DESC LIMIT 1").fetchone()
    if not row:
        return {"error": "No phone location recorded yet"}
    addr = reverse_geocode(row["lat"], row["lon"]) if row["lat"] and row["lon"] else {}
    return {"id": row["id"], "lat": row["lat"], "lon": row["lon"],
            "accuracy_m": row["accuracy"], "speed": row["speed"],
            "address": addr.get("display_name", "Unknown"),
            "source": row["source"], "ts": row["ts"]}

def _phone_location_history(db, args):
    rows = db.execute("SELECT * FROM phone_locations ORDER BY ts DESC LIMIT ?", (args.get("limit", 20),)).fetchall()
    return {"locations": [dict(r) for r in rows]}

def _geo_fence_create(db, args):
    db.execute("INSERT OR REPLACE INTO geo_fences (name, center_lat, center_lon, radius_m) VALUES (?,?,?,?)",
               (args["name"], args["center_lat"], args["center_lon"], args.get("radius_m", 100)))
    db.commit()
    return {"status": "ok", "fence": args["name"], "center": [args["center_lat"], args["center_lon"]], "radius_m": args.get("radius_m", 100)}

def _geo_fence_check(db, args):
    phone = db.execute("SELECT * FROM phone_locations ORDER BY ts DESC LIMIT 1").fetchone()
    if not phone:
        return {"error": "No phone location recorded. Use phone_location_set or wait for OwnTracks."}
    fences = db.execute("SELECT * FROM geo_fences WHERE enabled=1").fetchall()
    results = []
    for f in fences:
        dist = haversine_m(f["center_lat"], f["center_lon"], phone["lat"], phone["lon"])
        inside = dist <= f["radius_m"]
        results.append({"fence": f["name"], "center": [f["center_lat"], f["center_lon"]],
                        "radius_m": f["radius_m"], "distance_from_center_m": round(dist, 1),
                        "phone_is_inside": inside})
    return {"phone": {"lat": phone["lat"], "lon": phone["lon"], "ts": phone["ts"]}, "fences": results}

def _geo_fence_list(db, args):
    rows = db.execute("SELECT * FROM geo_fences ORDER BY name").fetchall()
    return {"fences": [dict(r) for r in rows]}

def _where_is_my_phone(db, args):
    phone = db.execute("SELECT * FROM phone_locations ORDER BY ts DESC LIMIT 1").fetchone()
    if not phone:
        return {"error": "No phone location recorded"}
    addr = reverse_geocode(phone["lat"], phone["lon"]) if phone["lat"] and phone["lon"] else {}
    result = {"phone": {"lat": phone["lat"], "lon": phone["lon"],
                        "address": addr.get("display_name", "Unknown"),
                        "last_seen": phone["ts"]}}
    if args.get("from_checkpoint"):
        cp = db.execute("SELECT * FROM checkpoints WHERE name=?", (args["from_checkpoint"],)).fetchone()
        if cp:
            dist = haversine_m(cp["lat"], cp["lon"], phone["lat"], phone["lon"])
            r = osrm_route(cp["lat"], cp["lon"], phone["lat"], phone["lon"], "walking")
            result["from_checkpoint"] = {"name": cp["name"], "lat": cp["lat"], "lon": cp["lon"]}
            result["straight_line_km"] = round(dist/1000, 2)
            if r.get("code") == "Ok" and r.get("routes"):
                result["road_distance_km"] = round(r["routes"][0]["distance"]/1000, 2)
                result["walk_time_min"] = round(r["routes"][0]["duration"]/60, 1)
    return result

TOOL_HANDLERS = {
    "checkpoint_set": _checkpoint_set,
    "checkpoint_get": _checkpoint_get,
    "checkpoint_list": _checkpoint_list,
    "checkpoint_delete": _checkpoint_delete,
    "track_start": _track_start,
    "track_point": _track_point,
    "track_end": _track_end,
    "track_summary": _track_summary,
    "distance_from_checkpoint": _distance_from_checkpoint,
    "distance_between": _distance_between,
    "geocode": _geocode,
    "reverse_geocode": _reverse_geocode,
    "phone_location_set": _phone_location_set,
    "phone_location_get": _phone_location_get,
    "phone_location_history": _phone_location_history,
    "geo_fence_create": _geo_fence_create,
    "geo_fence_check": _geo_fence_check,
    "geo_fence_list": _geo_fence_list,
    "where_is_my_phone": _where_is_my_phone,
}

# ---------------------------------------------------------------------------
# HTTP endpoint for OwnTracks phone GPS ingestion
# ---------------------------------------------------------------------------
def _run_http_server():
    """Minimal HTTP server for OwnTracks location POSTs."""
    import http.server
    class OwnTracksHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode() if length > 0 else "{}"
            try:
                data = json.loads(body) if body.startswith("{") else {}
                # OwnTracks JSON format: {"lat":..., "lon":..., "acc":..., "alt":..., "speed":..., "bearing":..., "t":"p"}
                lat, lon = data.get("lat"), data.get("lon")
                if lat is not None and lon is not None:
                    db = get_db()
                    db.execute("INSERT INTO phone_locations (lat, lon, accuracy, altitude, speed, bearing, source, ts) VALUES (?,?,?,?,?,?,'owntracks',datetime('now'))",
                               (lat, lon, data.get("acc"), data.get("alt"), data.get("speed"), data.get("bearing")))
                    db.commit()
                    db.close()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                    return
                # Also accept simple JSON: {"lat":..., "lon":...}
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Need lat, lon"}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                db = get_db()
                cp_count = db.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
                loc_count = db.execute("SELECT COUNT(*) FROM phone_locations").fetchone()[0]
                db.close()
                self.wfile.write(json.dumps({
                    "status": "ok", "checkpoints": cp_count, "phone_locations": loc_count,
                    "ownTracks_endpoint": f"POST /location  JSON body: {{\"lat\":...,\"lon\":...,\"acc\":...,\"alt\":...}}"
                }).encode())
            elif self.path == "/location":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"POST lat/lon JSON here. OwnTracks format accepted.")
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # silence logs
    
    server_instance = http.server.HTTPServer((HTTP_HOST, HTTP_PORT), OwnTracksHandler)
    print(f"[Geo-Tracker HTTP] Listening on {HTTP_HOST}:{HTTP_PORT} for OwnTracks GPS data")
    server_instance.serve_forever()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    # Start HTTP server in a background thread
    http_thread = threading.Thread(target=_run_http_server, daemon=True)
    http_thread.start()
    print(f"[Geo-Tracker MCP] Database: {DB_PATH}")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            InitializationOptions(
                server_name="geo-tracker",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
