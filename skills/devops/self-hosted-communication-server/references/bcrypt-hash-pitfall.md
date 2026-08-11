# BCrypt Hash Generation: Python vs Node.js Incompatibility

## The Problem

Spacebar uses Node.js `bcrypt.compare()` to verify passwords during login.
If you generate a bcrypt hash with **Python's `bcrypt` library** and store it
in the database, **Node.js may fail to verify it** — even though Python's
`bcrypt.checkpw()` confirms the hash is correct.

Both libraries produce hashes with the `$2b$` prefix (correct bcrypt version),
and the hash format is structurally identical. The failure is an observed
behavior difference between the two implementations on certain platforms
(Windows Python 3.11 bcrypt 5.0.0 vs Linux Node.js 20 bcrypt 2.x).

## Symptom

```python
# Python — works
import bcrypt
hash = bcrypt.hashpw(b"mypassword", bcrypt.gensalt(rounds=10))
bcrypt.checkpw(b"mypassword", hash)  # → True
```

```javascript
// Node.js — may fail with the SAME hash
const bcrypt = require('bcrypt');
bcrypt.compareSync("mypassword", hash);  // → false  ❌
```

The login endpoint returns `{"code":50035,"message":"Invalid Form Body"}`
with `INVALID_LOGIN` errors for both `login` and `password` fields, even
though the user exists and the hash is technically correct.

## Fix

**Always generate bcrypt hashes with Node.js** when the hash will be stored
in Spacebar's database:

```javascript
// Generate hash with Node.js (inside the Spacebar directory for correct bcrypt version)
cd /opt/spacebar
node -e "const b=require('bcrypt'); console.log(b.hashSync('password123', 10));"
// → $2b$10$...
```

Then store this hash in the database:

```sql
UPDATE users SET data = jsonb_set(COALESCE(data, '{}'::jsonb), '{hash}',
    '"$2b$10$..."') WHERE id = '<user_id>';
```

## Verification

After updating the hash, test login immediately:

```bash
curl -s -X POST http://localhost:3100/api/v9/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"username","password":"password123"}'
# → {"token":"eyJ..."}  ✅
```

If you still get `INVALID_LOGIN`, the issue is likely **not the hash** —
check for duplicate usernames, stale tokens, or schema validation (see
`fermi-login-compatibility.md`).

## Prevention

- Use Node.js for all password hash operations in Spacebar contexts
- In scripts that create/reset user passwords, run the hash generation
  via `subprocess.run(["node", "-e", "..."])` rather than Python bcrypt
- When using `psql` to update hashes, write the SQL to a file first to
  avoid shell escaping issues with `$` characters in the hash
