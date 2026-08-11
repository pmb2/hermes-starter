#!/usr/bin/env python3
"""
Usage Analytics Dashboard for Hermes Agent
===========================================
Generates a self-contained HTML dashboard from Hermes' state.db session database.
Shows: token usage trends, cost breakdowns, model usage, platform activity,
session stats, and more.

Run: python usage_dashboard.py [--days N] [--output PATH]

Outputs to ~/Documents/github/hermes-config/dashboard/report.html by default.
Also prints a text summary to stdout for cron delivery.
"""

import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html import escape

# === CONFIG ===
HERMES_HOME = os.path.expanduser("~/AppData/Local/hermes")
STATE_DB = os.path.join(HERMES_HOME, "state.db")
OUTPUT_DIR = os.path.expanduser("~/Documents/github/hermes-config/dashboard")
DEFAULT_DAYS = 30


def get_db() -> sqlite3.Connection:
    """Open the state database read-only."""
    if not os.path.exists(STATE_DB):
        print(f"ERROR: State DB not found at {STATE_DB}")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_sessions(conn: sqlite3.Connection, days: int) -> list[dict]:
    """Fetch sessions within the lookback window. Timestamps are Unix epoch floats."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    rows = conn.execute(
        """
        SELECT * FROM sessions
        WHERE started_at >= ?
        ORDER BY started_at DESC
        """,
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def fetch_model_usage(conn: sqlite3.Connection, days: int) -> list[dict]:
    """Fetch per-model usage breakdown within lookback. Timestamps are Unix epoch floats."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    rows = conn.execute(
        """
        SELECT * FROM session_model_usage
        WHERE last_seen >= ?
        ORDER BY last_seen DESC
        """,
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def compute_section(ctx: dict) -> dict:
    """Compute all dashboard sections from fetched data."""
    sessions = ctx["sessions"]
    model_usage = ctx["model_usage"]

    result = {}

    # --- Overview ---
    total_sessions = len(sessions)
    total_input_tokens = sum(s.get("input_tokens", 0) or 0 for s in sessions)
    total_output_tokens = sum(s.get("output_tokens", 0) or 0 for s in sessions)
    total_cache_read = sum(s.get("cache_read_tokens", 0) or 0 for s in sessions)
    total_cache_write = sum(s.get("cache_write_tokens", 0) or 0 for s in sessions)
    total_reasoning = sum(s.get("reasoning_tokens", 0) or 0 for s in sessions)
    total_token_estimate = (
        sum(s.get("estimated_cost_usd", 0) or 0 for s in sessions) +
        sum(m.get("estimated_cost_usd", 0) or 0 for m in model_usage)
    )
    total_messages = sum(s.get("message_count", 0) or 0 for s in sessions)
    total_tool_calls = sum(s.get("tool_call_count", 0) or 0 for s in sessions)
    total_api_calls = sum(s.get("api_call_count", 0) or 0 for s in sessions)

    result["overview"] = {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_tool_calls": total_tool_calls,
        "total_api_calls": total_api_calls,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cache_read": total_cache_read,
        "total_cache_write": total_cache_write,
        "total_reasoning": total_reasoning,
        "total_cost_estimate": round(total_token_estimate, 4),
        "days": ctx["days"],
    }

    # --- Token trend (by day) ---
    day_buckets: dict[str, dict] = {}
    for s in sessions:
        start_ts = s.get("started_at", 0) or 0
        day = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d") if start_ts else "unknown"
        if day not in day_buckets:
            day_buckets[day] = {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
                "reasoning": 0,
                "sessions": 0,
                "cost": 0.0,
            }
        day_buckets[day]["input"] += s.get("input_tokens", 0) or 0
        day_buckets[day]["output"] += s.get("output_tokens", 0) or 0
        day_buckets[day]["cache_read"] += s.get("cache_read_tokens", 0) or 0
        day_buckets[day]["cache_write"] += s.get("cache_write_tokens", 0) or 0
        day_buckets[day]["reasoning"] += s.get("reasoning_tokens", 0) or 0
        day_buckets[day]["sessions"] += 1
        day_buckets[day]["cost"] += s.get("estimated_cost_usd", 0) or 0

    sorted_days = sorted(day_buckets.keys())
    result["daily_trend"] = {
        "labels": sorted_days,
        "input": [day_buckets[d]["input"] for d in sorted_days],
        "output": [day_buckets[d]["output"] for d in sorted_days],
        "cache_read": [day_buckets[d]["cache_read"] for d in sorted_days],
        "cache_write": [day_buckets[d]["cache_write"] for d in sorted_days],
        "reasoning": [day_buckets[d]["reasoning"] for d in sorted_days],
        "sessions": [day_buckets[d]["sessions"] for d in sorted_days],
        "cost": [round(day_buckets[d]["cost"], 4) for d in sorted_days],
    }

    # --- Model breakdown ---
    model_tokens: dict[str, dict] = {}
    for m in model_usage:
        model_name = m.get("model", "unknown")
        if model_name not in model_tokens:
            model_tokens[model_name] = {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "cache_write": 0,
                "reasoning": 0,
                "calls": 0,
                "cost": 0.0,
                "provider": m.get("billing_provider", ""),
            }
        model_tokens[model_name]["input"] += m.get("input_tokens", 0) or 0
        model_tokens[model_name]["output"] += m.get("output_tokens", 0) or 0
        model_tokens[model_name]["cache_read"] += m.get("cache_read_tokens", 0) or 0
        model_tokens[model_name]["cache_write"] += m.get("cache_write_tokens", 0) or 0
        model_tokens[model_name]["reasoning"] += m.get("reasoning_tokens", 0) or 0
        model_tokens[model_name]["calls"] += m.get("api_call_count", 0) or 0
        model_tokens[model_name]["cost"] += m.get("estimated_cost_usd", 0) or 0

    sorted_models = sorted(model_tokens.keys(), key=lambda k: model_tokens[k]["cost"], reverse=True)
    result["model_breakdown"] = {
        "models": sorted_models,
        "input": [model_tokens[m]["input"] for m in sorted_models],
        "output": [model_tokens[m]["output"] for m in sorted_models],
        "calls": [model_tokens[m]["calls"] for m in sorted_models],
        "cost": [round(model_tokens[m]["cost"], 4) for m in sorted_models],
        "providers": [model_tokens[m]["provider"] for m in sorted_models],
    }

    # --- Source/platform breakdown ---
    source_count: Counter = Counter()
    source_tokens: defaultdict = defaultdict(lambda: {"input": 0, "output": 0})
    for s in sessions:
        src = s.get("source", "unknown")
        source_count[src] += 1
        source_tokens[src]["input"] += s.get("input_tokens", 0) or 0
        source_tokens[src]["output"] += s.get("output_tokens", 0) or 0

    sorted_sources = sorted(source_count.keys(), key=lambda k: source_count[k], reverse=True)
    result["source_breakdown"] = {
        "sources": sorted_sources,
        "counts": [source_count[s] for s in sorted_sources],
        "input": [source_tokens[s]["input"] for s in sorted_sources],
        "output": [source_tokens[s]["output"] for s in sorted_sources],
    }

    # --- Top sessions by cost ---
    sorted_sessions = sorted(sessions, key=lambda s: s.get("estimated_cost_usd", 0) or 0, reverse=True)[:15]
    result["top_sessions"] = [
        {
            "title": s.get("title", "Untitled"),
            "model": s.get("model", "?"),
            "source": s.get("source", "?"),
            "started": datetime.fromtimestamp(s.get("started_at", 0) or 0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if s.get("started_at") else "?",
            "messages": s.get("message_count", 0),
            "tool_calls": s.get("tool_call_count", 0),
            "api_calls": s.get("api_call_count", 0),
            "input_tokens": s.get("input_tokens", 0) or 0,
            "output_tokens": s.get("output_tokens", 0) or 0,
            "cost": round(s.get("estimated_cost_usd", 0) or 0, 4),
        }
        for s in sorted_sessions
        if s.get("title") and s.get("estimated_cost_usd", 0) or 0 > 0
    ]

    # --- Average session stats ---
    sessions_with_data = [s for s in sessions if s.get("message_count", 0) and s.get("message_count", 0) > 0]
    if sessions_with_data:
        avg_messages = sum(s["message_count"] for s in sessions_with_data) / len(sessions_with_data)
        avg_tool_calls = sum(s.get("tool_call_count", 0) or 0 for s in sessions_with_data) / len(sessions_with_data)
        avg_tokens_per_session = (
            sum((s.get("input_tokens", 0) or 0) + (s.get("output_tokens", 0) or 0) for s in sessions_with_data)
            / len(sessions_with_data)
        )
    else:
        avg_messages = avg_tool_calls = avg_tokens_per_session = 0

    result["averages"] = {
        "avg_messages": round(avg_messages, 1),
        "avg_tool_calls": round(avg_tool_calls, 1),
        "avg_tokens": round(avg_tokens_per_session, 0),
    }

    # --- Cost distribution ---
    cost_buckets = {"$0": 0, "$0.01-$0.10": 0, "$0.11-$1.00": 0, "$1.01+": 0}
    for s in sessions:
        c = s.get("estimated_cost_usd", 0) or 0
        if c == 0:
            cost_buckets["$0"] += 1
        elif c <= 0.10:
            cost_buckets["$0.01-$0.10"] += 1
        elif c <= 1.00:
            cost_buckets["$0.11-$1.00"] += 1
        else:
            cost_buckets["$1.01+"] += 1
    result["cost_distribution"] = cost_buckets

    # --- Hourly activity heatmap ---
    hourly: dict[int, int] = {h: 0 for h in range(24)}
    for s in sessions:
        try:
            dt = datetime.fromtimestamp(s.get("started_at", 0) or 0, tz=timezone.utc)
            h = dt.hour
            hourly[h] = hourly.get(h, 0) + 1
        except (ValueError, TypeError):
            pass
    result["hourly_activity"] = hourly

    return result


def generate_html(d: dict) -> str:
    """Generate the full HTML dashboard."""
    o = d["overview"]
    daily = d["daily_trend"]

    # Format numbers nicely
    def fmt(n):
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(n)

    # Build chart data as JSON for Chart.js
    daily_labels_json = json.dumps(daily["labels"])
    daily_input_json = json.dumps(daily["input"])
    daily_output_json = json.dumps(daily["output"])
    daily_cache_r_json = json.dumps(daily["cache_read"])
    daily_cache_w_json = json.dumps(daily["cache_write"])
    daily_reasoning_json = json.dumps(daily["reasoning"])
    daily_sessions_json = json.dumps(daily["sessions"])
    daily_cost_json = json.dumps(daily["cost"])

    mb = d["model_breakdown"]
    mb_models_json = json.dumps(mb["models"])
    mb_input_json = json.dumps([fmt(v) for v in mb["input"]])
    mb_output_json = json.dumps([fmt(v) for v in mb["output"]])
    mb_calls_json = json.dumps(mb["calls"])
    mb_cost_json = json.dumps(mb["cost"])

    sb = d["source_breakdown"]
    sb_sources_json = json.dumps(sb["sources"])
    sb_counts_json = json.dumps(sb["counts"])
    sb_input_json = json.dumps([fmt(v) for v in sb["input"]])
    sb_output_json = json.dumps([fmt(v) for v in sb["output"]])

    hourly = d["hourly_activity"]
    hourly_labels = json.dumps([f"{h:02d}:00" for h in range(24)])
    hourly_data = json.loads(json.dumps([hourly[h] for h in range(24)]))

    avg = d["averages"]

    # Top sessions table rows
    top_rows = ""
    for ts in d["top_sessions"]:
        top_rows += f"""<tr>
          <td>{escape(ts['title'][:60])}</td>
          <td>{escape(ts['model'][:30])}</td>
          <td>{escape(ts['source'])}</td>
          <td>{ts['started']}</td>
          <td>{ts['messages']}</td>
          <td>{fmt(ts['input_tokens'])}</td>
          <td>{fmt(ts['output_tokens'])}</td>
          <td>${ts['cost']}</td>
        </tr>"""

    # Cost distribution
    cd = d["cost_distribution"]
    cost_dist_json = json.dumps(list(cd.keys()))
    cost_dist_vals_json = json.dumps(list(cd.values()))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes Usage Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }}
h1 {{ font-size: 28px; margin-bottom: 8px; color: #58a6ff; }}
h2 {{ font-size: 20px; margin: 28px 0 16px; color: #f0f6fc; border-bottom: 1px solid #30363d; padding-bottom: 8px; }}
.subtitle {{ color: #8b949e; margin-bottom: 24px; font-size: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; text-align: center; }}
.card .val {{ font-size: 28px; font-weight: 700; color: #f0f6fc; }}
.card .label {{ font-size: 12px; color: #8b949e; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
.chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
.chart-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; }}
.chart-card.full {{ grid-column: 1 / -1; }}
.chart-card h3 {{ font-size: 14px; color: #8b949e; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
canvas {{ max-height: 300px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; padding: 10px 12px; background: #21262d; color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid #30363d; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #21262d; }}
tr:hover td {{ background: #1c2128; }}
.table-wrap {{ overflow-x: auto; }}
@media (max-width: 900px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>

<h1>📊 Hermes Usage Dashboard</h1>
<p class="subtitle">Last {o['days']} days — Generated {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>

<!-- Overview Cards -->
<div class="grid">
  <div class="card"><div class="val">{o['total_sessions']}</div><div class="label">Sessions</div></div>
  <div class="card"><div class="val">{fmt(o['total_messages'])}</div><div class="label">Messages</div></div>
  <div class="card"><div class="val">{fmt(o['total_tool_calls'])}</div><div class="label">Tool Calls</div></div>
  <div class="card"><div class="val">{fmt(o['total_api_calls'])}</div><div class="label">API Calls</div></div>
  <div class="card"><div class="val">{fmt(o['total_input_tokens'])}</div><div class="label">Input Tokens</div></div>
  <div class="card"><div class="val">{fmt(o['total_output_tokens'])}</div><div class="label">Output Tokens</div></div>
  <div class="card"><div class="val">{fmt(o['total_cache_read'])}</div><div class="label">Cache Read</div></div>
  <div class="card"><div class="val">{fmt(o['total_cache_write'])}</div><div class="label">Cache Write</div></div>
  <div class="card"><div class="val">{fmt(o['total_reasoning'])}</div><div class="label">Reasoning Tokens</div></div>
  <div class="card"><div class="val">${o['total_cost_estimate']:.4f}</div><div class="label">Est. Cost</div></div>
</div>

<!-- Charts -->
<div class="chart-grid">

  <!-- Daily Token Usage -->
  <div class="chart-card full">
    <h3>Daily Token Usage</h3>
    <canvas id="dailyTokensChart"></canvas>
  </div>

  <!-- Daily Sessions -->
  <div class="chart-card">
    <h3>Daily Sessions</h3>
    <canvas id="dailySessionsChart"></canvas>
  </div>

  <!-- Daily Cost -->
  <div class="chart-card">
    <h3>Daily Estimated Cost (USD)</h3>
    <canvas id="dailyCostChart"></canvas>
  </div>

  <!-- Model Cost Breakdown -->
  <div class="chart-card">
    <h3>Cost by Model</h3>
    <canvas id="modelCostChart"></canvas>
  </div>

  <!-- Model Calls -->
  <div class="chart-card">
    <h3>API Calls by Model</h3>
    <canvas id="modelCallsChart"></canvas>
  </div>

  <!-- Source/Platform -->
  <div class="chart-card">
    <h3>Sessions by Platform</h3>
    <canvas id="sourceChart"></canvas>
  </div>

  <!-- Hourly Activity -->
  <div class="chart-card">
    <h3>Hourly Activity (UTC)</h3>
    <canvas id="hourlyChart"></canvas>
  </div>

  <!-- Cost Distribution -->
  <div class="chart-card">
    <h3>Session Cost Distribution</h3>
    <canvas id="costDistChart"></canvas>
  </div>

  <!-- Averages -->
  <div class="chart-card">
    <h3>Averages per Session</h3>
    <div style="padding: 20px 0; text-align: center;">
      <div style="display: inline-block; margin: 0 24px;">
        <div style="font-size: 32px; font-weight: 700; color: #f0f6fc;">{avg['avg_messages']}</div>
        <div style="font-size: 12px; color: #8b949e;">Messages</div>
      </div>
      <div style="display: inline-block; margin: 0 24px;">
        <div style="font-size: 32px; font-weight: 700; color: #f0f6fc;">{avg['avg_tool_calls']}</div>
        <div style="font-size: 12px; color: #8b949e;">Tool Calls</div>
      </div>
      <div style="display: inline-block; margin: 0 24px;">
        <div style="font-size: 32px; font-weight: 700; color: #f0f6fc;">{fmt(avg['avg_tokens'])}</div>
        <div style="font-size: 12px; color: #8b949e;">Tokens/Session</div>
      </div>
    </div>
  </div>

  <!-- Top Sessions -->
  <div class="chart-card full">
    <h3>Top Sessions by Cost</h3>
    <div class="table-wrap">
    <table>
      <tr><th>Title</th><th>Model</th><th>Source</th><th>Started</th><th>Msg</th><th>In Tok</th><th>Out Tok</th><th>Cost</th></tr>
      {top_rows if top_rows else '<tr><td colspan="8" style="text-align:center;color:#8b949e;">No sessions with cost data</td></tr>'}
    </table>
    </div>
  </div>
</div>

<script>
// Daily Token Usage
new Chart(document.getElementById('dailyTokensChart'), {{
  type: 'bar',
  data: {{
    labels: {daily_labels_json},
    datasets: [
      {{label: 'Input', data: {daily_input_json}, backgroundColor: '#238636', borderRadius: 2}},
      {{label: 'Output', data: {daily_output_json}, backgroundColor: '#1f6feb', borderRadius: 2}},
      {{label: 'Cache Read', data: {daily_cache_r_json}, backgroundColor: '#8957e5', borderRadius: 2}},
      {{label: 'Cache Write', data: {daily_cache_w_json}, backgroundColor: '#d29922', borderRadius: 2}},
      {{label: 'Reasoning', data: {daily_reasoning_json}, backgroundColor: '#f85149', borderRadius: 2}},
    ]
  }},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, position: 'top'}}}},
    scales: {{x: {{ticks: {{color: '#8b949e'}}}}, y: {{ticks: {{color: '#8b949e'}}, beginAtZero: true}}}} }}
}});

// Daily Sessions
new Chart(document.getElementById('dailySessionsChart'), {{
  type: 'line',
  data: {{labels: {daily_labels_json}, datasets: [{{label: 'Sessions', data: {daily_sessions_json}, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', fill: true, tension: 0.3}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, display: false}}}},
    scales: {{x: {{ticks: {{color: '#8b949e'}}}}, y: {{ticks: {{color: '#8b949e'}}, beginAtZero: true}}}} }}
}});

// Daily Cost
new Chart(document.getElementById('dailyCostChart'), {{
  type: 'bar',
  data: {{labels: {daily_labels_json}, datasets: [{{label: 'Cost (USD)', data: {daily_cost_json}, backgroundColor: '#d29922', borderRadius: 2}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, display: false}}}},
    scales: {{x: {{ticks: {{color: '#8b949e'}}}}, y: {{ticks: {{color: '#8b949e'}}, beginAtZero: true}}}} }}
}});

// Model Cost
new Chart(document.getElementById('modelCostChart'), {{
  type: 'doughnut',
  data: {{labels: {mb_models_json}, datasets: [{{data: {mb_cost_json}, backgroundColor: ['#238636','#1f6feb','#8957e5','#d29922','#f85149','#58a6ff','#3fb950','#db6d28','#bc8c00','#a371f7']}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, position: 'right'}}}} }}
}});

// Model Calls
new Chart(document.getElementById('modelCallsChart'), {{
  type: 'bar',
  data: {{labels: {mb_models_json}, datasets: [{{label: 'API Calls', data: {mb_calls_json}, backgroundColor: '#8957e5', borderRadius: 2}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, display: false}}}},
    scales: {{x: {{ticks: {{color: '#8b949e'}}}}, y: {{ticks: {{color: '#8b949e'}}, beginAtZero: true}}}} }}
}});

// Source/Platform
new Chart(document.getElementById('sourceChart'), {{
  type: 'polarArea',
  data: {{labels: {sb_sources_json}, datasets: [{{data: {sb_counts_json}, backgroundColor: ['#238636','#1f6feb','#8957e5','#d29922','#f85149','#58a6ff']}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, position: 'right'}}}} }}
}});

// Hourly Activity
new Chart(document.getElementById('hourlyChart'), {{
  type: 'bar',
  data: {{labels: {hourly_labels}, datasets: [{{label: 'Session Starts', data: {json.dumps(hourly_data)}, backgroundColor: '#1f6feb', borderRadius: 2}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, display: false}}}},
    scales: {{x: {{ticks: {{color: '#8b949e'}}}}, y: {{ticks: {{color: '#8b949e'}}, beginAtZero: true}}}} }}
}});

// Cost Distribution
new Chart(document.getElementById('costDistChart'), {{
  type: 'pie',
  data: {{labels: {cost_dist_json}, datasets: [{{data: {cost_dist_vals_json}, backgroundColor: ['#238636','#1f6feb','#d29922','#f85149']}}]}},
  options: {{ responsive: true, plugins: {{legend: {{labels: {{color: '#8b949e'}}, position: 'right'}}}} }}
}});
</script>

</body>
</html>"""
    return html


def print_text_summary(d: dict):
    """Print a text summary for cron delivery."""
    o = d["overview"]
    daily = d["daily_trend"]
    mb = d["model_breakdown"]
    avg = d["averages"]

    print(f"📊 HERMES USAGE REPORT — Last {o['days']} Days")
    print(f"{'='*60}")
    print(f"  Sessions:     {o['total_sessions']}")
    print(f"  Messages:     {o['total_messages']}")
    print(f"  Tool Calls:   {o['total_tool_calls']}")
    print(f"  API Calls:    {o['total_api_calls']}")
    print(f"  Est. Cost:    ${o['total_cost_estimate']:.4f}")
    print()
    print(f"📈 TOKEN USAGE")
    print(f"  Input:        {o['total_input_tokens']:,}")
    print(f"  Output:       {o['total_output_tokens']:,}")
    print(f"  Cache Read:   {o['total_cache_read']:,}")
    print(f"  Cache Write:  {o['total_cache_write']:,}")
    print(f"  Reasoning:    {o['total_reasoning']:,}")
    print()
    print(f"📊 AVERAGES PER SESSION")
    print(f"  Messages:     {avg['avg_messages']}")
    print(f"  Tool Calls:   {avg['avg_tool_calls']}")
    print(f"  Tokens:       {avg['avg_tokens']:,.0f}")
    print()
    print(f"🤖 MODEL BREAKDOWN (by cost)")
    total_cost = sum(mb["cost"])
    for i, m in enumerate(mb["models"]):
        pct = (mb["cost"][i] / total_cost * 100) if total_cost > 0 else 0
        print(f"  {m[:40]:40s} ${mb['cost'][i]:.4f} ({pct:.1f}%)  {mb['calls'][i]} calls")
    print()
    print(f"📱 PLATFORM BREAKDOWN")
    for i, src in enumerate(d["source_breakdown"]["sources"]):
        print(f"  {src:20s} {d['source_breakdown']['counts'][i]} sessions")
    print()
    print(f"⏰ PEAK HOUR")
    peak_hour = max(d["hourly_activity"], key=d["hourly_activity"].get)
    print(f"  Most sessions start at: {peak_hour:02d}:00 UTC")
    print()
    print(f"💰 COST DISTRIBUTION")
    for bucket, count in d["cost_distribution"].items():
        print(f"  {bucket:20s} {count} sessions")
    print()
    print(f"📈 TOP SESSIONS BY COST")
    for ts in d["top_sessions"][:5]:
        print(f"  ${ts['cost']:.4f} — {ts['title'][:60]}")
    print()
    print(f"📁 Full HTML dashboard saved to output path")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Usage Analytics Dashboard")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"Lookback days (default: {DEFAULT_DAYS})")
    parser.add_argument("--output", type=str, default=os.path.join(OUTPUT_DIR, "report.html"), help="Output HTML path")
    args = parser.parse_args()

    conn = get_db()
    sessions = fetch_sessions(conn, args.days)
    model_usage = fetch_model_usage(conn, args.days)
    conn.close()

    ctx = {"sessions": sessions, "model_usage": model_usage, "days": args.days}
    data = compute_section(ctx)

    # Generate and save HTML
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    html = generate_html(data)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    # Print text summary
    print_text_summary(data)
    print(f"\n📁 Dashboard: {args.output}")
    print(f"   Open in browser to view charts")


if __name__ == "__main__":
    main()
