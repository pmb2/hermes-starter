# Namecheap DNS Configuration

## Domain: your-domain.example — Subdomain: doghouse.your-domain.example

Namecheap is the domain registrar. DNS is managed via Namecheap's default DNS (registrar-servers.com) or optionally delegated to Cloudflare.

## Default DNS (Namecheap BasicDNS)

### Current Status
- **Nameservers:** dns1.registrar-servers.com, dns2.registrar-servers.com
- No Cloudflare delegation

### A Record Configuration
| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | `doghouse` | `[VPS_IP_ADDRESS]` | Automatic (30 min) |
| A | `@` | `[VPS_IP_ADDRESS]` | Automatic (30 min) |
| A | `www` | `[VPS_IP_ADDRESS]` | Automatic (30 min) |

### CAA Record (required for Let's Encrypt SSL)
| Type | Name | Value | TTL |
|------|------|-------|-----|
| CAA | `@` | `0 issue "letsencrypt.org"` | 3600 |

### Remove Default/Unused Records
- Delete any default parking records (e.g., `@ 192.64.119.xxx`)
- Delete default URL redirect records (e.g., `@ → http://www.your-domain.example`)
- These cause Caddy to fail SSL provisioning because DNS resolves to wrong IP first

## Steps to Update

1. Log into **https://www.namecheap.com/**
2. Go to **Dashboard → Domain List**
3. Click **Manage** next to `your-domain.example`
4. Go to **Advanced DNS** tab
5. Edit the `doghouse` A record's value to the new VPS IP
6. Click ✓ checkmark to save
7. Wait **5-30 minutes** for propagation

## Verification

```bash
# DNS resolution check
nslookup doghouse.your-domain.example
# Expected: Address: [VPS_IP]

# Propagation check (bypass local cache)
nslookup doghouse.your-domain.example 1.1.1.1
nslookup doghouse.your-domain.example 8.8.8.8

# CAA record check
nslookup -type=CAA your-domain.example
# Expected: your-domain.example  CAA record 0 issue "letsencrypt.org"
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| DNS resolves to wrong IP | Old A record not updated | Edit A record on Namecheap Advanced DNS |
| Caddy SSL fails | CAA record missing | Add CAA: `0 issue "letsencrypt.org"` |
| SSL "connection refused" | DNS not propagated yet | Wait 30 min, check with `nslookup` |
| App returns "Welcome to nginx" | No Caddy config | Upload Caddyfile, `sudo systemctl reload caddy` |

## Alternative: Cloudflare Proxy

If you want Cloudflare proxying (CDN, DDoS protection, hidden origin IP):
1. Add the domain to Cloudflare
2. Change nameservers on Namecheap to Cloudflare's
3. Set the A record on Cloudflare (orange cloud = proxied)
4. Caddy still handles SSL on the origin server via Cloudflare Origin CA or self-signed cert
