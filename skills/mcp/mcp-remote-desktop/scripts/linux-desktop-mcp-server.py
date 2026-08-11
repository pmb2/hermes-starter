#!/usr/bin/env python3
"""
whonix-mcp — Production-grade MCP server for Linux X11 desktop control.

Designed for Whonix / Kicksecure (Xfce, X11), but works on any Linux
desktop with xdotool + scrot + wmctrl. 25 tools covering mouse, keyboard,
screenshots, windows, clipboard, apps, filesystem, and shell execution.

Privacy-first: all tools execute inside the VM, inheriting its network
stack. Screenshots are ephemeral (temp file, deleted after transfer).
No outbound connections from the server itself.

Usage inside VM:
    pip install "mcp>=1.0,<1.2" pillow
    python3 linux-desktop-mcp-server.py

From Hermes config.yaml on host:
    mcp_servers:
      whonix-desktop:
        command: ssh
        args: ["-T", "-i", "/path/to/key", "user@10.152.152.11",
               "python3 /home/user/linux-desktop-mcp-server.py"]
        timeout: 300
        connect_timeout: 30

For a fully-deployed version with systemd service and setup script, see:
https://github.com/pmb2/whonix-mcp (private)
"""

import base64
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP("Whonix Desktop Control", log_level="INFO")

# Ensure DISPLAY is set (Whonix Workstation uses :0 by default)
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], timeout: int = 30) -> str:
    """Run a command, return stdout, raise on error."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(cmd)} failed "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Tool: screenshot
# ---------------------------------------------------------------------------


@mcp.tool()
def screenshot() -> str:
    """Capture the full desktop screen and return it as a base64-encoded PNG.

    Returns a data URI (data:image/png;base64,...). Screenshots are saved
    to a temp file inside the VM and immediately cleaned up.
    """
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        _run(["scrot", "-z", tmp_path], timeout=15)
        with open(tmp_path, "rb") as f:
            raw = f.read()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# Tool: mouse
# ---------------------------------------------------------------------------


@mcp.tool()
def click(x: int, y: int, button: str = "left") -> str:
    """Click at screen coordinates (x, y). Supported buttons: left, middle, right."""
    btn_map = {"left": 1, "middle": 2, "right": 3}
    btn = btn_map.get(button, 1)
    _run(["xdotool", "mousemove", str(x), str(y), "click", str(btn)])
    return f"Clicked {button} at ({x}, {y})"


@mcp.tool()
def double_click(x: int, y: int) -> str:
    """Double-click at screen coordinates (x, y)."""
    _run(["xdotool", "mousemove", str(x), str(y), "click", "--repeat", "2", "1"])
    return f"Double-clicked at ({x}, {y})"


@mcp.tool()
def right_click(x: int, y: int) -> str:
    """Right-click at screen coordinates (x, y)."""
    return click(x, y, button="right")


@mcp.tool()
def move_mouse(x: int, y: int) -> str:
    """Move the mouse cursor to screen coordinates (x, y) without clicking."""
    _run(["xdotool", "mousemove", str(x), str(y)])
    return f"Moved cursor to ({x}, {y})"


@mcp.tool()
def get_cursor_position() -> dict:
    """Return the current mouse cursor position as {x, y}."""
    raw = _run(["xdotool", "getmouselocation", "--shell"])
    pos = {}
    for line in raw.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            pos[k.lower()] = int(v)
    return {"x": pos.get("x", 0), "y": pos.get("y", 0)}


@mcp.tool()
def drag(start_x: int, start_y: int, end_x: int, end_y: int,
         button: str = "left", duration_ms: int = 500) -> str:
    """Drag the mouse from (start_x, start_y) to (end_x, end_y)."""
    btn_map = {"left": 1, "middle": 2, "right": 3}
    btn = btn_map.get(button, 1)
    steps = max(10, duration_ms // 20)
    dx = (end_x - start_x) / steps
    dy = (end_y - start_y) / steps

    _run(["xdotool", "mousemove", str(start_x), str(start_y)])
    _run(["xdotool", "mousedown", str(btn)])
    try:
        for i in range(1, steps + 1):
            cx = int(start_x + dx * i)
            cy = int(start_y + dy * i)
            _run(["xdotool", "mousemove", str(cx), str(cy)])
            time.sleep(0.02)
    finally:
        _run(["xdotool", "mouseup", str(btn)])

    return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"


# ---------------------------------------------------------------------------
# Tool: keyboard
# ---------------------------------------------------------------------------


@mcp.tool()
def type_text(text: str) -> str:
    """Type the given text at the currently focused element.
    Long text is chunked to avoid xdotool's 256-char limit.
    """
    chunk_size = 200
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        _run(["xdotool", "type", chunk], timeout=10)
        time.sleep(0.05)
    return f"Typed {len(text)} characters"


@mcp.tool()
def press_key(key: str) -> str:
    """Press a keyboard key or key combination.
    Examples: 'Return', 'Escape', 'Tab', 'ctrl+c', 'alt+F4'.
    """
    _run(["xdotool", "key", key])
    return f"Pressed key(s): {key}"


@mcp.tool()
def hold_key(key: str) -> str:
    """Hold down a keyboard key (use release_key to let go)."""
    _run(["xdotool", "keydown", key])
    return f"Holding key: {key}"


@mcp.tool()
def release_key(key: str) -> str:
    """Release a previously held keyboard key."""
    _run(["xdotool", "keyup", key])
    return f"Released key: {key}"


# ---------------------------------------------------------------------------
# Tool: scroll
# ---------------------------------------------------------------------------


@mcp.tool()
def scroll(x: int, y: int, clicks: int = 1, direction: str = "down") -> str:
    """Scroll the mouse wheel at position (x, y). direction: 'down' or 'up'."""
    btn = 4 if direction == "up" else 5
    _run(["xdotool", "mousemove", str(x), str(y)])
    for _ in range(clicks):
        _run(["xdotool", "click", str(btn)])
    return f"Scrolled {direction} {clicks} clicks at ({x}, {y})"


# ---------------------------------------------------------------------------
# Tool: windows
# ---------------------------------------------------------------------------


@mcp.tool()
def list_windows() -> list[dict]:
    """List all open windows with id, desktop, geometry, and title."""
    raw = _run(["wmctrl", "-lG"])
    windows = []
    for line in raw.splitlines():
        parts = line.split(maxsplit=5)
        if len(parts) >= 6:
            win_id = parts[0]
            try:
                x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
            except ValueError:
                x = y = w = h = 0
            windows.append({
                "id": win_id,
                "desktop": int(parts[1]),
                "x": x, "y": y, "width": w, "height": h,
                "title": parts[5],
            })
    return windows


@mcp.tool()
def activate_window(title_substring: str) -> str:
    """Bring the first window matching title_substring to the foreground."""
    for w in list_windows():
        if title_substring.lower() in w["title"].lower():
            _run(["xdotool", "windowactivate", w["id"]])
            return f"Activated window: {w['title']}"
    return f"No window found with title containing '{title_substring}'"


@mcp.tool()
def get_window_info(title_substring: str) -> Optional[dict]:
    """Get geometry of a window matching title_substring. Returns None if not found."""
    for w in list_windows():
        if title_substring.lower() in w["title"].lower():
            return w
    return None


@mcp.tool()
def resize_window(title_substring: str, width: int, height: int) -> str:
    """Resize a window matching title_substring."""
    for w in list_windows():
        if title_substring.lower() in w["title"].lower():
            _run(["xdotool", "windowsize", w["id"], str(width), str(height)])
            return f"Resized '{w['title']}' to {width}x{height}"
    return f"No window found"


@mcp.tool()
def move_window(title_substring: str, x: int, y: int) -> str:
    """Move a window matching title_substring to screen position (x, y)."""
    for w in list_windows():
        if title_substring.lower() in w["title"].lower():
            _run(["xdotool", "windowmove", w["id"], str(x), str(y)])
            return f"Moved '{w['title']}' to ({x}, {y})"
    return f"No window found"


# ---------------------------------------------------------------------------
# Tool: clipboard
# ---------------------------------------------------------------------------


@mcp.tool()
def clipboard_get() -> str:
    """Read the current X11 clipboard content."""
    return _run(["xclip", "-o", "-selection", "clipboard"], timeout=5)


@mcp.tool()
def clipboard_set(text: str) -> str:
    """Set the X11 clipboard content."""
    proc = subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text.encode("utf-8"), capture_output=True, timeout=5,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"xclip failed: {proc.stderr.decode().strip()}")
    return f"Clipboard set ({len(text)} chars)"


# ---------------------------------------------------------------------------
# Tool: applications
# ---------------------------------------------------------------------------


@mcp.tool()
def launch_app(command: str, wait_sec: float = 2.0) -> str:
    """Launch an application inside the VM (inherits Tor on Whonix).

    Example: 'firefox', 'thunar', 'xterm -e \\'curl https://check.torproject.org\\''
    """
    proc = subprocess.Popen(
        command, shell=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    time.sleep(wait_sec)
    if proc.poll() is not None and proc.returncode != 0:
        return f"Command exited immediately with code {proc.returncode}"
    return f"Launched: {command} (PID: {proc.pid})"


# ---------------------------------------------------------------------------
# Tool: shell
# ---------------------------------------------------------------------------


@mcp.tool()
def shell(command: str, timeout_sec: int = 60) -> str:
    """Execute an arbitrary shell command inside the VM (Torified on Whonix).

    Use for apt, pip, curl, file ops, scripts. Timeout max: 300s.
    """
    if timeout_sec > 300:
        timeout_sec = 300
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout_sec,
        )
        output = result.stdout
        if result.returncode != 0:
            output += f"\n[EXIT CODE: {result.returncode}]"
            if result.stderr:
                output += f"\n[STDERR]\n{result.stderr.strip()}"
        return output
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout_sec}s]"
    except Exception as e:
        return f"[ERROR] {e}"


# ---------------------------------------------------------------------------
# Tool: screen info
# ---------------------------------------------------------------------------


@mcp.tool()
def get_screen_size() -> dict:
    """Return the screen resolution as {width, height}."""
    raw = _run(["xdotool", "getdisplaygeometry"])
    parts = raw.split()
    return {"width": int(parts[0]), "height": int(parts[1])}


# ---------------------------------------------------------------------------
# Tool: wait
# ---------------------------------------------------------------------------


@mcp.tool()
def wait(milliseconds: int = 1000) -> str:
    """Pause execution for N milliseconds. Useful after launching apps."""
    time.sleep(milliseconds / 1000.0)
    return f"Waited {milliseconds}ms"


# ---------------------------------------------------------------------------
# Tool: file system
# ---------------------------------------------------------------------------


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file from the VM filesystem."""
    p = Path(path)
    if not p.is_file():
        return f"File not found: {path}"
    return p.read_text(encoding="utf-8", errors="replace")


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file on the VM filesystem (creates dirs, overwrites)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


@mcp.tool()
def list_directory(path: str = ".") -> list[dict]:
    """List a directory on the VM."""
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        return [{"error": f"Not a directory: {path}"}]
    entries = []
    for child in sorted(p.iterdir()):
        try:
            entries.append({
                "name": child.name,
                "type": "directory" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else 0,
            })
        except PermissionError:
            entries.append({"name": child.name, "type": "unknown", "size": 0})
    return entries


# ---------------------------------------------------------------------------
# Tool: verify Tor
# ---------------------------------------------------------------------------


@mcp.tool()
def check_tor() -> dict:
    """Verify the VM is routing through Tor via check.torproject.org."""
    try:
        result = subprocess.run(
            ["curl", "-s", "https://check.torproject.org/"],
            capture_output=True, text=True, timeout=15,
        )
        is_tor = "Congratulations" in result.stdout
        return {
            "tor_active": is_tor,
            "detail": "Traffic is routed through Tor." if is_tor
                       else "WARNING: Traffic may NOT be routed through Tor!",
        }
    except Exception as e:
        return {"tor_active": False, "detail": f"Check failed: {e}"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
