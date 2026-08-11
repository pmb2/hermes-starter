#!/usr/bin/env python3
"""
Postiz API Client — ready-to-use HTTP client for the Postiz REST API.

Use this in Hermes cron jobs, subagents, or any Python script that needs
to post to social media through Postiz.

Usage:
  export POSTIZ_API_KEY="your-api-key"
  export POSTIZ_API_URL="http://localhost:4007/api"   # self-hosted
  python postiz-api-client-pattern.py

Or hardcode base_url + api_key (not recommended for shared scripts).
"""

import os
import json
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API_KEY = os.environ.get("POSTIZ_API_KEY", "")
BASE_URL = os.environ.get("POSTIZ_API_URL", "http://localhost:4007/api")


def _headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def _request(method, path, data=None):
    url = f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=_headers(), method=method)
    try:
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}


# ── Discovery ──────────────────────────────────────────────────────────

def list_integrations(group=None):
    """List connected social accounts. Optionally filter by group (customer) ID."""
    path = "/public/v1/integrations"
    if group:
        path += f"?group={group}"
    return _request("GET", path)


def list_groups():
    """List all groups (customers) in the organization."""
    return _request("GET", "/public/v1/groups")


# ── Posts ──────────────────────────────────────────────────────────────

def create_post(content, schedule_date, integration_ids,
                media_urls=None, post_type="schedule", comments=None,
                settings=None):
    """
    Schedule or draft a post.

    Args:
        content: Main post text.
        schedule_date: ISO 8601 datetime string (e.g. "2025-01-15T14:00:00Z").
        integration_ids: List of integration IDs to post to.
        media_urls: Optional list of media URLs (images/videos).
        post_type: "schedule" (default) or "draft".
        comments: Optional list of comment text strings.
        settings: Optional platform-specific settings dict.

    Returns:
        Created post object or error.
    """
    payload = {
        "content": content,
        "date": schedule_date,
        "integrations": integration_ids,
        "type": post_type,
    }
    if media_urls:
        payload["media"] = media_urls
    if comments:
        payload["comments"] = [{"content": c} for c in comments]
    if settings:
        payload["settings"] = settings
    return _request("POST", "/public/v1/posts", payload)


def list_posts(start_date=None, end_date=None, customer=None):
    """List posts, with optional date range filter."""
    params = {}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    if customer:
        params["customer"] = customer
    path = "/public/v1/posts"
    if params:
        path += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return _request("GET", path)


def delete_post(post_id):
    """Delete a scheduled post by ID."""
    return _request("DELETE", f"/public/v1/posts/{post_id}")


def change_post_status(post_id, status):
    """Change post status: 'draft' or 'schedule'."""
    return _request("PUT", f"/public/v1/posts/{post_id}/status",
                    {"status": status})


# ── Analytics ──────────────────────────────────────────────────────────

def platform_analytics(integration_id, days=7):
    """Get analytics for a connected platform over N days."""
    return _request("GET",
                    f"/public/v1/analytics/{integration_id}",
                    {"days": days})


def post_analytics(post_id, days=7):
    """Get analytics for a specific post over N days."""
    return _request("GET",
                    f"/public/v1/analytics/post/{post_id}",
                    {"days": days})


# ── Media ──────────────────────────────────────────────────────────────

def upload_media(file_path):
    """Upload a media file. Returns URL usable in create_post()."""
    import mimetypes
    from urllib.parse import urlparse

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mimetypes.guess_type(file_path)[0] or 'application/octet-stream'}\r\n\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    url = f"{BASE_URL.rstrip('/')}/public/v1/upload"
    req = Request(url, data=body,
                  headers={**{"Content-Type": f"multipart/form-data; boundary={boundary}"},
                           **{"Authorization": f"Bearer {API_KEY}"}})
    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            return result.get("url", result)
    except HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}


# ── Example ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Postiz API Client Demo ===\n")

    if not API_KEY:
        print("ERROR: Set POSTIZ_API_KEY environment variable")
        exit(1)

    # 1. List integrations
    integrations = list_integrations()
    print(f"Integrations: {json.dumps(integrations, indent=2)}\n")

    if isinstance(integrations, list) and len(integrations) > 0:
        integ_id = integrations[0].get("id")
        # 2. Get integration settings
        settings = _request("GET", f"/public/v1/integration-settings/{integ_id}")
        print(f"Settings for {integ_id}: {json.dumps(settings, indent=2)[:500]}\n")

        # 3. Schedule a test post
        tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT12:00:00Z")
        result = create_post(
            content="Test post from Hermes API client 🤖",
            schedule_date=tomorrow,
            integration_ids=[integ_id],
        )
        print(f"Create post result: {json.dumps(result, indent=2)}\n")
    else:
        print("No integrations connected yet. Connect social accounts in the Postiz UI first.\n")

    # 4. List groups
    groups = list_groups()
    print(f"Groups: {json.dumps(groups, indent=2)}")
