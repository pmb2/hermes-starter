# Desktop Control MCP Server Landscape

Full research results from investigating MCP servers for VM desktop
control (June 2026). Sorted by platform and maturity.

## How to evaluate a candidate MCP server

1. **Check the tool list** — does it have screenshot capture, mouse
   click/move, keyboard input, and window management? Those are the
   minimum viable set for desktop control.
2. **Test in isolation** before wiring to Hermes. Run the MCP SDK's
   standalone test script against it (see `native-mcp` skill).
3. **Check the star count and last commit date** — many are abandonware.
4. **Verify the platform** — Windows-MCP is Windows-only, kwin-mcp is
   KDE/Wayland-only, etc.

## Linux / X11 (Whonix, Ubuntu, Debian, generic Linux VM)

### Custom xdotool + scrot + Python MCP server (recommended for Whonix)

The most reliable approach for Whonix (Xfce/X11). ~100 lines of Python.

**Dependencies:**
```
sudo apt install xdotool scrot wmctrl xclip x11-utils xautomation
pip install mcp pillow
```

**Minimal tools to expose:**
- `screenshot` — runs `scrot` (or `import -window root`), returns base64
- `click` — `xdotool mousemove X Y click 1`
- `double_click` — `xdotool mousemove X Y click 1 click 1`
- `right_click` — `xdotool mousemove X Y click 3`
- `move_mouse` — `xdotool mousemove X Y`
- `type_text` — `xdotool type --delay 10 "text"`
- `press_key` — `xdotool key Return`
- `key_combo` — `xdotool key ctrl+c`
- `list_windows` — `wmctrl -l` parsed into structured list
- `activate_window` — `wmctrl -a "window title"`
- `get_cursor_pos` — `xdotool getmouselocation`
- `get_screen_size` — `xdotool getdisplaygeometry`
- `clipboard_get` — `xclip -o -selection clipboard`
- `clipboard_set` — `xclip -selection clipboard`

**Transport:** Connect via SSH stdio tunnel (see SKILL.md).

### computer-control-mcp / AB498
- **Stars:** 148
- **Stack:** PyAutoGUI, RapidOCR, ONNXRuntime
- **Install:** `uvx computer-control-mcp@latest`
- **Tools:** Mouse click/move/drag, type text, press keys, screenshots,
  OCR, list/activate windows, screen size, wait
- **Platform:** Cross-platform (Linux, Windows, macOS)
- **Notes:** Zero external deps beyond pip. OCR is nice for reading
  text from screenshots. Linux support is functional but basic — no
  accessibility tree, no Wayland support.
- **Review:** Solid minimal option. PyAutoGUI on Linux uses Xlib under
  the hood so it works on X11 (Whonix). ~70MB download first time.

### taw-computer / the-agents-work
- **Stars:** 8
- **Stack:** Docker + Xfce + Chromium + VNC
- **Install:** `git clone + docker build + npm start`
- **Tools:** 30+ tools — full desktop control, browser automation via
  CDP, shell, file system, screenshot, process management
- **Platform:** Ubuntu Docker container, accessed via MCP
- **Notes:** NOT for controlling an existing VM — it creates a new
  Ubuntu sandbox. Good as an alternative if you want a clean disposable
  desktop instead of Whonix. VNC access for live viewing.
- **Review:** Turnkey solution if you don't need Whonix's Tor routing.
  Container snapshots persist across sessions.

### kwin-mcp / isac322
- **Stars:** 29
- **Stack:** KWin Wayland, AT-SPI2 accessibility tree, libei input
- **Install:** `uv tool install kwin-mcp` then add to MCP config
- **Tools:** 30 tools — virtual/live sessions, mouse, keyboard, touch,
  clipboard, AX tree inspection, screenshots, window management
- **Platform:** KDE Plasma 6 Wayland ONLY
- **Notes:** Cannot use on Whonix (Xfce/X11). Has a unique "virtual
  session" mode that runs apps in isolated `dbus-run-session` + KWin.
  Live session mode can connect to a real desktop.
- **Review:** Best option if you ever switch to KDE/Wayland. The AT-SPI2
  accessibility tree is a major advantage — agent can read structured
  UI elements without relying on vision.

### clawdcursor / AmrDab
- **Stars:** 386
- **Stack:** Accessibility tree + OCR fusion → stable addresses
- **Platform:** Cross-platform (was macOS, expanding)
- **Notes:** Unique approach — compiles on-screen content into stable,
  addressable elements. Screenshot only when needed. Safety gate on
  every action.
- **Review:** Promising approach but still maturing.

## Windows (desktop or Windows VM)

### Windows-MCP / CursorTouch
- **Stars:** 6,223 ★ (most popular)
- **Stack:** Python + UIAutomation + native Windows APIs
- **Install:** `uvx windows-mcp serve`
- **Tools (17):** Click, Type, Scroll, Move, Shortcut, Wait, WaitFor,
  Screenshot, Snapshot (AX tree), App, PowerShell, FileSystem, Scrape,
  MultiSelect, MultiEdit, Clipboard, Process, Notification, Registry
- **Platform:** Windows 7–11
- **Notes:** 2M+ users. Listed in Claude Desktop directory. Supports
  SSE and StreamableHTTP transports. Has auth, IP allowlisting, TLS,
  OAuth 2.0 + PKCE. Mature security model.
- **Review:** The gold standard for Windows MCP desktop control. If
  you're controlling a Windows VM (e.g., Windows in VirtualBox), this
  is the server to run inside it.

### nutjs-windows-control
- **Stars:** N/A
- **Stack:** Nut.js (Node.js, cross-platform desktop automation)
- **Install:** `npx @nutjs/windows-control-mcp`
- **Platform:** Windows
- **Notes:** Node.js-based alternative to Windows-MCP. Less mature.
- **Review:** Listed on mcpservers.org. Good if you prefer JS stack.

### computer-control-mcp / AB498
(Same as Linux section — works on Windows too)
- Windows has better support: WGC (Windows Graphics Capture) for GPU
  windows, avoids black screens with Electron/browser apps.

### clawdcursor / AmrDab
(Same as Linux section — works on Windows)

## macOS (macOS VM / remote Mac)

### macuse-mcp / macuse-app
- **Stars:** 34
- **Stack:** Accessibility API, AppleScript
- **Install:** `npx mac-use-mcp`
- **Tools:** Mouse, keyboard, screenshots, Calendar, Mail, Notes, etc.
- **Platform:** macOS 13+
- **Notes:** App-specific tools beyond raw desktop control.
- **Review:** Best option for macOS desktop control.

### desktop-pilot-mcp / VersoXBT
- **Stars:** 10
- **Stack:** AX API + AppleScript + CGEvent
- **Notes:** Claims 30-100x faster than screenshot-based computer-use.
  Uses semantic element targeting.

## Remote transport comparison

| Transport | Security | Complexity | Best for |
|-----------|----------|------------|----------|
| SSH stdio (Hermes spawns `ssh user@vm python3 server.py`) | SSH encryption, key auth | Low — no extra daemons | Linux VMs with SSH access |
| HTTP/SSE over SSH tunnel (`ssh -L 8000:localhost:8000`) | SSH tunnel + optional TLS | Medium — requires port forwarding | Any platform |
| Direct HTTP with auth+TLS | Customizable via --auth-key | Medium — needs open port | When SSH is unavailable |
| StreamableHTTP with OAuth | OAuth 2.0 + PKCE | High | Production deployments |

## Whonix-specific reference

- Whonix Workstation: `10.152.152.11` (internal IP, host-routable)
- Whonix Gateway: `10.152.152.10`
- Desktop: Xfce (X11, not Wayland)
- Tools: `xdotool`, `scrot`, `wmctrl` are your automation stack
- SSH: Enable with `sudo systemctl enable --now ssh`
- Python: ships with Python 3 — install `pip install mcp pillow`
- Network: Workstation routes through Gateway/Tor by default. The SSH
  connection from the host goes through the Gateway and is NOT Torified
  (it's the host→Gateway→Workstation path). This is fine.
- Gotcha: Whonix's AppArmor may restrict `scrot` or `xdotool` — check
  `sudo aa-status` if tools fail. May need to adjust profiles.
- Gotcha: Whonix Template VM has no persistent storage by default in
  some setups (Qubes edition). For the non-Qubes VirtualBox edition,
  this isn't an issue.
