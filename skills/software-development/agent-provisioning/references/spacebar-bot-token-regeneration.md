# Spacebar Bot User Creation & Token Regeneration

## When to Use This

Use when:
- A Hermes profile exists locally but has no matching bot user in the Spacebar database
- Bot tokens were lost or overwritten (all profiles share the same token)
- Tokens need rotating (security rotation)

## Prerequisites

- SSH access to VPS: `ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190`
- VPS has Node.js and `pg` module (already installed in /opt/spacebar)
- VPS has `/opt/spacebar/gen-vps-tokens.js` token generation script
- VPS has `/opt/spacebar/.env` with DATABASE connection string

## Step 1: Create Missing Bot Users

Bot users don't auto-create when you create a Hermes profile. They must be created in the Spacebar PostgreSQL database:

```bash
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190
cd /opt/spacebar
node -e "
const { Client } = require('pg');
require('dotenv').config();

async function main() {
    const client = new Client({ connectionString: process.env.DATABASE });
    await client.connect();

    const BOTS = ['bot-name-1', 'bot-name-2', 'bot-name-3'];
    for (let i = 0; i < BOTS.length; i++) {
        const uname = BOTS[i];
        const exists = await client.query('SELECT id FROM users WHERE username=$1', [uname]);
        if (exists.rows.length > 0) {
            console.log('EXISTS: ' + uname);
            continue;
        }
        const epoch = 1420070400000n;
        const now = BigInt(Date.now()) - epoch;
        const id = (now << 22n) | (1n << 17n) | (1n << 12n) | BigInt(i + 1);

        await client.query(
            'INSERT INTO users (id, username, discriminator, email, desktop, mobile, premium, premium_type, bot, bio, system, nsfw_allowed, mfa_enabled, created_at, verified, disabled, deleted, flags, public_flags, purchased_flags, premium_usage_flags, rights, data, fingerprints, webauthn_enabled) VALUES ($1, $2, $3, $4, false, false, true, 2, true, $5, false, true, false, NOW(), true, false, false, 0, 0, 0, 0, $6, $7::jsonb, $8, false)',
            [id.toString(), uname, '0001', uname + '@bot.local', '', '0', '{}', '{}']
        );
        console.log('CREATED: ' + uname);
    }

    const r = await client.query('SELECT count(*) as cnt FROM users WHERE bot=true');
    console.log('Total bots: ' + r.rows[0].cnt);
    await client.end();
}
main().catch(e => { console.log('ERR: ' + e.message); process.exit(1); });
"
```

The INSERT statement uses all columns that Spacebar's schema expects. If the schema changes, check an existing working script like `/opt/spacebar/create-all-bots-db6.js` for the exact column list.

## Step 2: Generate Fresh JWT Tokens

```bash
cd /opt/spacebar && node gen-vps-tokens.js
```

This script:
1. Queries all bot users from the DB
2. Deletes old sessions
3. Creates a new session per bot with a random TOK_ session ID
4. Signs a JWT with the ES512 private key (`jwt.key`)
5. Writes all tokens to `/opt/spacebar/vps-bot-tokens.env`

Output looks like:
```
Wrote 44 tokens to /opt/spacebar/vps-tokens.env
Testing chief-of-staff token...
Auth response: {"id":"<discord-channel-id>","username":"chief-of-staff",...}
```

## Step 3: Download & Inject Tokens Locally

```bash
# Download from VPS
ssh -i ~/.ssh/oracle_vps ubuntu@129.153.156.190 'cat /opt/spacebar/vps-bot-tokens.env' > ${USER_HOME}/vps-tokens.env

# Inject into profiles
python ${HERMES_HOME}/skills/software-development/agent-provisioning/scripts/inject-bot-tokens.py
```

## Step 4: Restart Fleet & Verify

```bash
cd ${MY_REPOS}/relay-pool && python fleet-manager.py deploy

# Verify identities in logs
grep "Connected as" ~/AppData/Local/hermes/profiles/*/logs/gateway.log | tail -20
```

Every profile should show `<profile-name>#0001`, not a sibling's name.

## Verification Script (Standalone)

```bash
# Quick token audit — checks all profiles for duplicate tokens
python -c "
import os, re
profiles = os.path.expanduser('~/AppData/Local/hermes/profiles')
seen = {}
for d in sorted(os.listdir(profiles)):
    env = os.path.join(profiles, d, '.env')
    if os.path.exists(env):
        with open(env) as f:
            m = re.search(r'DISCORD_BOT_TOKEN\s*=\s*(\S+)', f.read())
        if m:
            mid = m.group(1).strip()[30:60]
            if mid in seen:
                print(f'DUPE: {d} == {seen[mid]}')
            else:
                seen[mid] = d
print(f'Unique tokens: {len(seen)} out of {len(os.listdir(profiles))} profiles')
"
```

## Common Pitfalls

- **Token file doesn't include new bots** — `gen-vps-tokens.js` only processes users with `bot=true` in the DB. If you created users but forgot to set `bot=true`, they won't get tokens.
- **JWT tokens share the first 25+ characters** — All JWTs start with `eyJhbGciOiJ...` (the base64-encoded header). Don't compare first 20 chars to check uniqueness. Compare chars 30-60 instead.
- **Gateway reads .env at startup** — After injecting tokens, the running gateway processes still have the old tokens. Must restart fleet.
- **gen-vps-tokens.js expects dotenv** — It reads DATABASE from the .env file. Run it from `/opt/spacebar/` directory.
- **File path mismatch on Windows** — The terminal tool uses MSYS paths (`${USER_HOME}/...`) but Python uses Windows paths (`${USER_HOME}/...`). Always use `${USER_HOME}/...` format in Python scripts.
