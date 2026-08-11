# Oracle Cloud Free Tier Client Onboarding

> Step-by-step handoff workflow for a non-technical client (e.g., Cody) to create their own free Oracle Cloud account and VPS so the agency can deploy their application without sharing the master account.

## When to use this model

- The master Oracle account (`<your-email>@gmail.com`) is already at its Always Free instance limit.
- The client does NOT need a paid account for a small business website.
- The client can be trusted to create an account and share credentials/IP with the agency operator.
- The target workload is a low-traffic local-service website (e.g., Chesapeake Mobile Detailing) or a small Docker Compose stack.

## What the client needs

- A personal email address (Gmail works).
- A credit or debit card. Oracle charges a small amount (~$1) and refunds it for identity verification.
- A phone that can receive an SMS verification code.
- About 30 minutes of uninterrupted time.

## Client steps

### 1. Sign up

1. Visit `https://www.oracle.com/cloud/free/`.
2. Click **Start for free**.
3. Choose the home country and enter the email.
4. Click the verification link in the email.
5. Complete the account form:
   - First / Last name
   - Password
   - Cloud account name (e.g., `chesapeake-mobile`)
   - Home region: **US East (Ashburn)**
6. Add the credit/debit card for identity verification.
7. Accept the terms and submit.
8. Wait for the account to be provisioned (usually under 5 minutes).

### 2. Create an SSH key

#### Windows (PowerShell)

```powershell
ssh-keygen -t ed25519 -C "cody@example.com" -f "$env:USERPROFILE\.ssh\chesapeake_vps"
```

Press Enter twice when prompted for a passphrase.

Result:

- `C:\Users\<User>\.ssh\chesapeake_vps` — private key.
- `C:\Users\<User>\.ssh\chesapeake_vps.pub` — public key.

Send the **public key** contents to the agency operator.

### 3. Create the VPS

1. Open the Oracle Console at `https://cloud.oracle.com/`.
2. Sign in with the cloud account name and credentials.
3. Open the **navigation menu** (hamburger) and choose **Compute → Instances**.
4. Click **Create instance**.
5. Set:
   - Name: `chesapeake-vps`
   - Image: **Canonical Ubuntu 24.04** or **Ubuntu 22.04**
   - Shape: **VM.Standard.E2.1.Micro** — must show "Always Free eligible"
   - Networking: keep the default
   - SSH key: paste the **public key** from Step 2
   - Boot volume: keep the default
6. Click **Create** and wait for the status to become **RUNNING**.

### 4. Open the firewall

1. Go to **Compute → Instances** and click `chesapeake-vps`.
2. Under **Primary VNIC**, click the **Subnet** link.
3. Click the **Default Security List**.
4. Add ingress rules for TCP ports `80` and `443` from source `0.0.0.0/0`.

### 5. Send the operator these items

- Cloud account name and username (email).
- VPS public IP address.
- The private SSH key file (`chesapeake_vps`).
- Confirmation that ports 80 and 443 are open.
- Confirmation that the instance shape is `VM.Standard.E2.1.Micro`.

## Operator steps after handoff

1. Update the A record for the client's domain at the domain registrar to the VPS public IP.
2. Connect via SSH using the provided key and the `ubuntu` user.
3. Install Docker, Caddy, and other required services.
4. Clone or copy the project repository.
5. Create the production `.env` file with generated secrets.
6. Build and start the Docker stack.
7. Verify the site loads over HTTPS.

## Why this works for the client

- No monthly charge if they stay on the Always Free tier.
- The site runs 24/7 on Oracle's infrastructure.
- The account remains in their name, so they keep ownership.
- The agency operator handles all technical configuration.

## Common pitfalls

- Do not choose **Oracle Linux**. Use **Ubuntu**.
- Do not upgrade to **Pay as you go** unless paid resources are needed.
- Make sure the shape says **Always Free eligible**.
- Do not share the **private key** with anyone other than the trusted operator.
