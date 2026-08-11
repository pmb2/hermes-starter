# Discord Bot Authorization via Developer Portal + Chrome DevTools MCP

> Created: June 23, 2026  
> Source: Chief of Staff Discord bot activation session

## Overview

When a Discord bot application already exists but needs to be authorized to a server (or needs intents/permissions updated), the Developer Portal is the canonical interface. Use Chrome DevTools MCP tools to drive the browser, since the REST API is blocked by hCaptcha for bot creation and MFA for token operations.

## Finding an Existing Application

Before creating a new bot application (which triggers hCaptcha), check if one already exists:

1. Navigate to `https://discord.com/developers/applications`
2. Look for the application by name (e.g., "CoS Chief of Staff", "Hermes Agent")
3. Existing apps have `Reset Token` on the Bot page — if you see that, a bot exists and can be reused

**When a bot already exists in the server** (was previously authorized), you can skip the invite step. Just configure intents and start the gateway with the token.

## Browser-Based Authorization Flow (via Chrome DevTools MCP)

### Step 1: Configure Installation Settings

1. Go to `https://discord.com/developers/applications/{app_id}/installation`
2. Ensure **Guild Install** is checked (not just User Install)
3. Under **Guild Install → Scopes:** — click the combobox, select `bot` from the dropdown list
4. Under **Guild Install → Permissions:** — click the combobox, select `Administrator` (or specific permissions)
5. Click **Save Changes**

The generated install link will now include `scope=bot+applications.commands` and `permissions=8` (Administrator).

### Step 2: Enable Required Gateway Intents

1. Go to `https://discord.com/developers/applications/{app_id}/bot`
2. Enable these intents under **Privileged Gateway Intents**:
   - **Message Content Intent** — REQUIRED for reading message content in channels
   - **Server Members Intent** — REQUIRED for knowing members and their roles
   - **Presence Intent** — Optional, only if you need presence data
3. Use `document.querySelectorAll('[role="switch"]')` to find and click the switches:
   - Switch [4] (index 4) = Message Content Intent (5th switch overall)
   - Switch [3] (index 3) = Server Members Intent (4th switch overall)
   - These are after 2 auth-flow switches (Public Bot + OAuth2 Code Grant)

### Step 3: Authorize the Bot to a Server

1. Navigate to the install URL: `https://discord.com/api/oauth2/authorize?client_id={app_id}&permissions=8&scope=bot%20applications.commands`
2. The authorization page shows:
   - Bot icon and name
   - Permissions summary
   - Server selector dropdown (pre-selects a server you have Manage Server permission on)
   - "Authorize" button
3. Select the target server (e.g., "Automation Team")
4. Click **Continue** → then **Authorize**
5. Success page confirms: "has been authorized and added to {server}"

### Step 4: Start the Gateway

With the bot token in the profile's `.env`:

```bash
cd ~/.hermes/profiles/{profile-name}/
hermes gateway run --profile {profile-name} --replace
```

Check connection:

```bash
cat ~/.hermes/profiles/{profile-name}/gateway_state.json
# Expected: "discord": {"state": "connected"}
```

## Handling Token Operations

### Reset Token (MFA Required)
The `Reset Token` button on the Bot page triggers **Discord Multi-Factor Authentication**. The MFA dialog asks for the account password. Available verification methods on this UI:
- **Password** (primary option)
- **Use your password** (if "Verify with something else" is clicked, it only goes back to password)

**This cannot be bypassed.** If the token was already copied at creation time, it's stored in the profile's `restore_env.py` or `.env` file. If those are missing/lost, you need the operator's password or an MFA code.

### The `restore_env.py` Pattern
When a bot token is successfully generated, a `restore_env.py` script is placed in the profile directory with the token hardcoded. This acts as a fallback if the `.env` file is overwritten:

```python
# restore_env.py template
token = "eyJ..."  # JWT token (for Spacebar) or MTA... (for Discord)
with open(path, 'w') as f:
    f.write(f"DISCORD_BOT_TOKEN={token}\n\nOPENROUTER_API_KEY=\n")
```

**Key insight:** The restore_env.py token may be a Spacebar JWT (starts with `eyJ`) or a Discord bot token (starts with `MT`). Check the token format before using it.

## Adding the Bot to a Server's Channel

After authorization, the bot has `Administrator` or the specified permissions. It can:
- Read messages in all channels it has access to
- Send messages
- Create threads
- Manage channels (if Administrator)

To let the bot respond in a specific channel, update the profile's `config.yaml`:

```yaml
discord:
  require_mention: false
  free_response_channels:
    - {channel_id}   # responds without @mention
  allowed_channels:
    - {channel_id}   # can respond here
```

Then restart the gateway to pick up the config change.

## Chrome DevTools MCP Context Notes

When driving the Developer Portal via `mcp_chrome_devtools_mcp_evaluate_script`:

- The function runs in an **isolated execution context** — `localStorage` is NOT defined, `document.cookie` returns non-HttpOnly cookies only
- For Discord's React SPA, native DOM events work: `element.click()` triggers React's synthetic event system
- `document.querySelectorAll('[role="switch"]')` finds all switch toggles — use `.click()` on each
- Dropdown/combobox options appear as `<li role="option">` elements in a `<ul role="listbox">` — click the option to select it
- The `mcp_chrome_devtools_mcp_fill_form` tool can fill multiple fields at once
- Tab navigation via `mcp_chrome_devtools_mcp_press_key("Tab")` works for SPAs that support keyboard nav
- Page navigation via `mcp_chrome_devtools_mcp_navigate_page` changes the URL and re-renders the SPA

## Pitfalls

- **MFA blocks token reset** — The `Reset Token` button always triggers MFA. The only workaround is if the token was saved elsewhere (restore_env.py, .env backup, council-tokens.env). You cannot get a fresh token without the operator's password/MFA code.
- **New app creation blocked by hCaptcha** — Use existing apps when possible. The Installation page approach (scopes + permissions) works without creating new apps.
- **Gateway must restart for config changes** — Editing config.yaml (allowed_channels, etc.) only takes effect after `hermes gateway run --replace`.
- **Bot token may be a Spacebar JWT** — If the profile was set up for Spacebar, the token in .env or restore_env.py might be a JWT (`eyJ...`) not a Discord bot token (`MT...`). These are NOT interchangeable. Discord gateway won't connect with a Spacebar token.
- **Intents must be enabled on the Developer Portal** — Even if the bot has Administrator permission, it won't receive message content unless the Message Content Intent is toggled ON in the Bot settings page. This is a separate toggle from permissions.
