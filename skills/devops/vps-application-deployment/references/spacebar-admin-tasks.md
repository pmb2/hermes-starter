# Spacebar Admin Tasks

## Reset User Password via Database

When a user cannot log in (forgotten password, no record of the password anywhere), reset it directly in the PostgreSQL database:

### Prerequisites
- SSH access to VPS
- Database credentials (from `.env`: `DATABASE=postgres://hamilton:***@127.0.0.1:5432/spacebar`)
- Docker running the Postgres container (typical setup)

### Steps

1. **Find the user:**

   ```bash
   sudo docker exec -i mobile-mechanic_postgres_1 psql -U hamilton -d spacebar \
     -c "SELECT id, username, email FROM users WHERE username = 'the operator'"
   ```

2. **Generate a bcrypt hash of the new password:**

   ```bash
   cd /opt/spacebar && \
   node -e "const bcrypt = require('bcrypt'); console.log(bcrypt.hashSync('NewPassword123!', bcrypt.genSaltSync(10)));"
   ```

   bcrypt lives in Spacebar's `node_modules` — run the command from `/opt/spacebar` so `require('bcrypt')` resolves. Running from `$HOME` gives `MODULE_NOT_FOUND`.

3. **Update the password hash in the database:**

   ```bash
   HASH=$(cd /opt/spacebar && node -e "const bcrypt = require('bcrypt'); console.log(bcrypt.hashSync('NewPassword123!', bcrypt.genSaltSync(10)));")
   
   sudo docker exec -i mobile-mechanic_postgres_1 psql -U hamilton -d spacebar \
     -c "UPDATE users SET data = jsonb_set(COALESCE(data, '{}'::jsonb), '{hash}', '\"$HASH\"', true) WHERE username = 'the operator'"
   ```

4. **Verify the update:**

   ```bash
   sudo docker exec -i mobile-mechanic_postgres_1 psql -U hamilton -d spacebar \
     -c "SELECT username, data->>'hash' AS hash_prefix FROM users WHERE username='the operator'"
   ```

5. **Test login:**

   ```bash
   curl -s -X POST -H "Content-Type: application/json" \
     -d '{"login":"the operator@your-domain.example","password":"NewPassword123!"}' \
     "https://gc.your-domain.example/api/v9/auth/login"
   ```

   A successful response includes `"user_id"` and `"token"`.

### How It Works

Spacebar stores each user's data as a JSONB column called `data`. The password hash lives at `data.hash`. The `jsonb_set` function updates or inserts the hash key without touching other user data (settings, guild positions, etc.).

The `COALESCE(data, '{}'::jsonb)` handles the edge case where data is NULL — creates an empty object first.

### Pitfalls

- **Shell quoting:** The hash contains `$` characters that the shell interprets as variable expansion. Wrap the HASH variable in double quotes (`"$HASH"`) inside the SQL string, and the SQL string in single quotes to prevent the shell from eating the JSON quotes.
- **bcrypt location:** Run `node` from `/opt/spacebar` (or wherever Spacebar's `node_modules` is). Running from any other directory gets `MODULE_NOT_FOUND` because bcrypt isn't globally installed.
- **Docker container name:** The Postgres container may have a different name on different deployments. Find it with `docker ps | grep postgres`.
