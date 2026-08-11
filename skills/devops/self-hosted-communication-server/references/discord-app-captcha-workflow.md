# Discord App Creation — CAPTCHA Workflow

Creating applications on Discord's developer portal always triggers an hCaptcha challenge. Two approaches below.

## Browser Automation (Playwright)

```python
# CRITICAL: Check captcha BEFORE checking URL for app ID
await page.goto("https://discord.com/developers/applications")
# ... click "New Application", fill name, submit ...

body = await page.inner_text("body")          # ✅ First: check captcha
if "captcha" in body.lower():
    # Wait up to 60s for user to solve
    pass

url = page.url                                 # ✅ Second: extract app ID
app_id = re.search(r'/applications/(\d+)', url)
```

**Pitfalls:**
- ❌ Checking URL for ID **before** CAPTCHA → "No ID" fail, page state corrupted
- ❌ SPA navigation between bots → page context crashes
- ✅ Fresh `context.new_page()` per bot, `page.goto()` for navigation
- ✅ `--non-interactive` flag to skip `input()` in background mode

## CapSolver Integration (Fully Automated)

Discord's API returns structured captcha data on app creation:

```python
resp = requests.post("https://discord.com/api/v9/applications",
    json={"name": "Bot Name"},
    headers={"Authorization": user_token})
if resp.status_code == 400 and "captcha_key" in resp.json():
    captcha = resp.json()
    # Fields: captcha_sitekey, captcha_session_id, captcha_rqdata, captcha_service
    # Submit sitekey to CapSolver/2captcha → get solution → retry with X-Captcha-Key header
```

Cost: ~$0.40-1.00/1k solves (~$0.01 for 9 bots). Services: CapSolver, 2captcha, Anti-Captcha.

## Three Bot Account Creation Methods

| Method | When to Use |
|--------|-------------|
| **A) Direct Self-Hosted API** | No CAPTCHA, preferred for Spacebar. `POST /v9/applications` + `POST /v9/applications/{id}/bot` |
| **B) Browser Automation** | Real Discord app, when hCaptcha is acceptable |
| **C) Direct DB Insert** | Bulk / rate-limit bypass — bypasses API entirely |
