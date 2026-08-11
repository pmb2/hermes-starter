# Namecheap DNS Setup for GitHub Pages

> **Registrar:** Namecheap.com  
> **DNS type:** Namecheap BasicDNS (registrar-servers.com) — no nameserver change needed  
> **Records needed:** 4 A records (apex) + 1 CNAME (www)

---

## ⚠️ IMPORTANT: CNAME timing

**Do NOT add the `CNAME` file to the GitHub repo until DNS has propagated.** If you add CNAME before the domain points to GitHub, the site will 404 everywhere (the default GitHub Pages URL gets disabled, and the custom domain doesn't resolve yet).

**Correct sequence:**
1. I deploy site to GitHub Pages (no CNAME file)
2. Site is live at `https://<user>.github.io/<repo>/`
3. You complete DNS steps below
4. Wait for propagation
5. Verify DNS resolves (`nslookup yourdomain.com` shows GitHub IPs)
6. **Tell me** — I'll add the CNAME file and the site flips to `https://yourdomain.com/`

---

## Step-by-step

### 1. Log into Namecheap.com
- Top-right **"Login"** button
- Use your Namecheap account credentials

### 2. Navigate to Domain List
- From the dashboard, click **"Domain List"** in the left sidebar
- Find your domain → click the blue **"Manage"** button on the right

### 3. Open Advanced DNS
- On the domain management page, look for the **"Advanced DNS"** tab near the top center
- Click it — you'll see a table of existing DNS records

### 4. Delete the old parking A record
- Find the existing `A` record with Host `@` and Value `162.255.119.240` (Namecheap's parking page)
- Click the **trash can / delete icon** on the right side of that row
- If there are multiple old records, delete any that aren't the new GitHub IPs

### 5. Add 4 A records (apex domain)
Click **"Add New Record"** four times, once per IP:

| # | Type dropdown | Host field | Value field | TTL |
|---|---|---|---|---|
| 1 | `A + Dynamic DNS` | `@` | `185.199.108.153` | `30 min` |
| 2 | `A + Dynamic DNS` | `@` | `185.199.109.153` | `30 min` |
| 3 | `A + Dynamic DNS` | `@` | `185.199.110.153` | `30 min` |
| 4 | `A + Dynamic DNS` | `@` | `185.199.111.153` | `30 min` |

**For each one:**
1. Select **A + Dynamic DNS** from the Type dropdown
2. Leave Host as **@** (means the bare domain, e.g., `yourdomain.com`)
3. Paste the GitHub Pages IP into the **Value** field
4. Set TTL to **30 min**
5. Click the green **✓** (checkmark) to confirm

### 6. Add CNAME for www subdomain
Click **"Add New Record"** one more time:

| Type dropdown | Host field | Value field | TTL |
|---|---|---|---|
| `CNAME` | `www` | `<your-github-username>.github.io` | `30 min` |

**Important:** The Value must be `<username>.github.io` (e.g., `your-username.github.io`), NOT `yourdomain.com`. A CNAME cannot point to another apex domain.

### 7. Save all changes
- Click the green **"Save All Changes"** button at the bottom of the DNS records table
- Namecheap will show a success message: "All changes were saved successfully"
- Propagation typically takes 5-30 minutes (up to 48 hours in rare cases)

---

## Verification

| Tool | Command / URL | Expected Result |
|---|---|---|
| DNS check | `nslookup yourdomain.com` | Returns 185.199.x.x IPs |
| Site check | `https://yourdomain.com` | Page loads with lock icon |
| www check | `https://www.yourdomain.com` | Redirects to apex |
| Propagation tracker | [whatsmydns.net](https://www.whatsmydns.net/#A/yourdomain.com) | Shows GitHub IPs globally |

---

## Troubleshooting

### "I can't find the Advanced DNS tab"
- Make sure you clicked **"Manage"** on the actual domain, not "Dashboard"
- On the Manage page, the tab is near the top center — might be hidden behind a narrow viewport
- Try scrolling horizontally or zooming out

### "Add New Record button isn't showing"
- Refresh the page in your browser
- Try a different browser (Chrome or Firefox)
- Clear cache if you've been on the page a while

### "Changes saved but site still shows parking page"
- Wait 15-30 minutes for propagation
- Verify you deleted the old `162.255.119.240` record
- Check at [whatsmydns.net](https://www.whatsmydns.net) — if some regions still show the old IP, it's still propagating

### "DNS shows GitHub IPs but site still returns Namecheap page"
- **Check for URL Forwarding:** Namecheap has a separate "URL Forwarding" feature (in the Domain tab, not Advanced DNS) that intercepts HTTP requests regardless of DNS A records. Response headers show `X-Served-By: Namecheap URL Forward`.
- If URL Forwarding is active, disable it:
  1. In Namecheap → Domain List → Manage → **Domain** tab (not Advanced DNS)
  2. Look for "URL Forwarding" section
  3. Delete any existing forwarding rules
  4. Wait a few minutes and retry
- This is NOT the same as DNS records — it operates at their proxy layer above DNS.

### "GitHub says domain not configured"
- Make sure the `CNAME` file in the repo has exactly `yourdomain.com` (no www, no trailing slash)
- Wait for DNS to fully propagate before GitHub accepts the domain
- In Settings → Pages, you may need to re-enter the domain after DNS updates

### "Enforce HTTPS is stuck / won't turn on"
- GitHub auto-provisions a Let's Encrypt certificate
- This only works AFTER DNS resolves to the GitHub IPs
- Can take up to 30 minutes from resolution
- Try unchecking "Enforce HTTPS", saving, then re-checking and saving again
