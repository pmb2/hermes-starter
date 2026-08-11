# OCI Ampere A1 Provisioning — Capacity Retry & CLI Setup

## OCI CLI Setup (from Windows)

### Prerequisites
- OCI API key pair (PEM format) generated from OCI web console
- User OCID, Tenancy OCID, Fingerprint, Region

### Config file (`~/.oci/config`)
```
[DEFAULT]
user=ocid1.user.oc1..<user-ocid>
fingerprint=15:dd:a2:9d:92:06:fd:84:b6:3f:a9:af:f8:3a:08:eb
tenancy=ocid1.tenancy.oc1..<tenancy-ocid>
region=us-ashburn-1
key_file=C:\Users\<user>\.oci\oci_api_key.pem
```

**Windows path note:** Use native Windows paths (`C:\Users\...`) in the config, not MSYS paths (`/c/Users/...`). The OCI CLI is a Windows Python process.

### Verify auth
```bash
oci iam availability-domain list \
  --compartment-id ocid1.tenancy.oc1..<tenancy-ocid>
# Returns 3 ADs (oRwF:US-ASHBURN-AD-1/2/3)
```

### Suppress file permission warnings (Windows)
```bash
export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True
```

---

## Instance Launch Commands

### Get the Ubuntu 22.04 ARM64 image
```bash
oci compute image list \
  --compartment-id ocid1.tenancy.oc1..<tenancy-ocid> \
  --operating-system "Canonical Ubuntu" \
  --operating-system-version "22.04" \
  --shape "VM.Standard.A1.Flex"
```

Latest as of June 2026: `Canonical-Ubuntu-22.04-aarch64-2026.04.30-1`

### Launch instance (fire-and-forget — no wait)
```bash
oci compute instance launch \
  --compartment-id ocid1.tenancy.oc1..<tenancy-ocid> \
  --availability-domain "oRwF:US-ASHBURN-AD-1" \
  --display-name "instance-name" \
  --image-id ocid1.image.oc1.iad.<image-ocid> \
  --shape "VM.Standard.A1.Flex" \
  --shape-config '{"ocpus":2,"memory-in-gbs":12}' \
  --subnet-id ocid1.subnet.oc1.iad.<subnet-ocid> \
  --assign-public-ip true \
  --ssh-authorized-keys-file ~/.ssh/key.pub \
  --boot-volume-size-in-gbs 200
```

**⚠️ Do NOT use `--wait-for-state RUNNING`** — it blocks until provisioning finishes, which can take 2+ minutes and timeout in CLI sessions. Launch fire-and-forget, then poll manually.

---

## Capacity Retry Loop

### The problem
Oracle free tier Ampere A1 shapes in us-ashburn-1 frequently return:
```json
{"code": "InternalError", "message": "Out of host capacity."}
```
This affects ALL ADs and ALL sizes (1-4 OCPU). The capacity opens and closes at random times.

### Retry loop pattern (background process, with timeout)
```bash
#!/bin/bash
export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True

for attempt in $(seq 1 60); do
  for ad in "oRwF:US-ASHBURN-AD-1" "oRwF:US-ASHBURN-AD-2" "oRwF:US-ASHBURN-AD-3"; do
    # timeout 30 prevents the API call from hanging for 2+ minutes
    # when the OCI backend is overloaded
    result=$(timeout 30 oci compute instance launch \
      --compartment-id <tenancy-ocid> \
      --availability-domain "$ad" \
      --display-name "instance-name" \
      --image-id <image-ocid> \
      --shape "VM.Standard.A1.Flex" \
      --shape-config '{"ocpus":2,"memory-in-gbs":12}' \
      --subnet-id <subnet-ocid> \
      --assign-public-ip true \
      --ssh-authorized-keys-file ~/.ssh/key.pub \
      --boot-volume-size-in-gbs 200 2>&1)

    if ! echo "$result" | grep -q "Out of host capacity"; then
      echo "SUCCESS in $ad!"
      echo "$result"
      exit 0
    fi
  done
  sleep 300  # 5 minutes
done
echo "All attempts exhausted"
exit 1
```

**Expected behavior:** The API call itself may take 30-120 seconds to respond (OCI is slow when capacity is tight). Each full cycle (3 ADs) can take 3-10 minutes. Total loop = 60 attempts * 5 min = 5 hours max.

### Resize after provisioning
Once the instance is RUNNING (even at small config):
```bash
# Stop instance
oci compute instance action --instance-id <ocid> --action STOP

# Update shape
oci compute instance update --instance-id <ocid> \
  --shape VM.Standard.A1.Flex \
  --shape-config '{"ocpus":4,"memory-in-gbs":24}'

# Start
oci compute instance action --instance-id <ocid> --action START
```

---

## Checking Provisioning Status

After a fire-and-forget launch, check if the instance exists:
```bash
oci compute instance list \
  --compartment-id <tenancy-ocid> \
  --display-name "instance-name"
```

Get the public IP once it's running:
```bash
# Get instance OCID first
INSTANCE_ID=$(oci compute instance list \
  --compartment-id <tenancy-ocid> \
  --display-name "instance-name" 2>/dev/null | \
  python -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])")

# Get VNIC attachment
VNIC_ID=$(oci compute vnic-attachment list \
  --compartment-id <tenancy-ocid> \
  --instance-id "$INSTANCE_ID" 2>/dev/null | \
  python -c "import sys,json; print(json.load(sys.stdin)['data'][0]['vnic-id'])")

# Get public IP
oci network vnic get --vnic-id "$VNIC_ID" 2>/dev/null | \
  python -c "import sys,json; print(json.load(sys.stdin)['data']['public-ip'])"
```

---

## Mitigation: Upgrade to Pay-As-You-Go (PAYG)

### The single most effective fix for "Out of host capacity"

Oracle's own documentation states:
> *"You can also choose to upgrade your account to Pay as You Go or another Paid account type, which gives you access to more types of Compute resources. Remember that Oracle doesn't charge for Always Free resources after you upgrade."*

**Upgrading to PAYG:**
- Moves you from the **free tier capacity pool** (oversubscribed) to the **paid capacity pool** (much more available)
- **Always Free resources remain $0/mo** — you're only charged if you provision non-free resources
- A credit card is required for identity verification but won't be charged for Always Free usage
- Can be done from the OCI Console: **Upgrade link** in the banner or **Account Management → Upgrade and Manage Payment**

### 🚫 PAYG blocked — $100 authorization hold

**Important limitation:** Oracle places a $100 authorization hold on the credit card when upgrading to PAYG. This is NOT a charge — it's a temporary hold that may take 5-7 business days to release. For strictly $0-budget operations, this hold makes PAYG infeasible.

**When PAYG is blocked, fall back to the retry loop above.** With 1 OCPU / 6 GB minimum config, capacity opens more frequently than at 4/24. Once the instance is RUNNING, resize it to 4/24 via stop → update shape → start.

### Upgrade path

1. Navigate to `https://cloud.oracle.com/account-management/payment-method`
2. Add a credit card (required for identity verification)
3. Select **Pay As You Go** plan
4. Click **Upgrade your account**
5. No budget or limit setup is required — can be skipped or set to $0

### After upgrading

- Set `OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True` before CLI calls
- Retry the same instance launch commands — capacity issues typically resolve immediately
- The same home region and ADs are used; no VCN/subnet changes needed
- If still blocked, set up the retry loop from the previous section — it typically succeeds within minutes on PAYG

### PAYG also enables multi-region

After upgrading to PAYG, you CAN subscribe to additional regions:
```bash
oci iam region-subscription create \
  --region-key PHX \
  --tenancy-id ocid1.tenancy.oc1..<tenancy-ocid>
```

This enables provisioning Ampere A1 instances in **us-phoenix-1** (US West) or other regions with better capacity — the common workaround when us-ashburn-1 is persistently full.

---

## API Key Generation (OCI Web Console)

When you need to generate an OCI API key for CLI/SDK access:

### Prerequisites
- OCI Console access (logged in at cloud.oracle.com)
- Admin user or permissions to manage own API keys

### Steps (via OCI Domains UI)

1. Navigate to **Identity & Security → Domains → Default domain**
2. Click **My profile** in the left sidebar
3. Click **Tokens and keys** tab
4. Scroll to **API keys** section
5. Click **Add API key**
6. Select **Generate API key pair** (default)
7. Click **Download private key** — saves `{email}-{timestamp}.pem`
8. Click **Add** to register the key's public key with your user
9. The fingerprint is displayed — copy it for OCI config

### Key details to capture

| Field | Source |
|-------|--------|
| User OCID | Profile page (under user info) or OCI CLI: `oci iam user list` |
| Tenancy OCID | Tenancy details page or VPS metadata `curl -s http://169.254.169.254/opc/v1/instance/` |
| Fingerprint | Shown in API keys list after adding |
| Private key | Downloaded `.pem` file |
| Public key | Downloaded `.pem` with `_public` suffix |

### Config file location
- **Windows:** `C:\Users\<user>\.oci\config`
- **Linux/Mac:** `~/.oci/config`

### Finding User OCID via OCI Console

Can't find the profile page URL? The OCI Domains UI loads in an iframe (`#sandbox-maui-preact-container`). Navigate to:
1. The user menu (top-right)
2. "My profile"  
3. The URL pattern: `https://cloud.oracle.com/identity/domains/my-profile`
4. User OCID is shown in the **User information** section under "OCID"

For programmatic access from within a signed-in session, use the iframe's contentDocument to find and click elements.

---

## Subscribed Regions Limitation

OCI free tier accounts are limited to **1 subscribed region** (the home region). Attempting to subscribe to another region without upgrading returns:

```json
{"code": "TenantCapacityExceeded",
 "message": "You have exceeded the maximum number of allowed subscribed regions."}
```

**To check subscribed regions:**
```bash
oci iam region-subscription list --region us-ashburn-1

# Returns only us-ashburn-1 for a standard free tier account
```

**Implications:**
- Cannot provision in us-phoenix-1, eu-frankfurt-1, or any other region
- Must use the home region's ADs (1, 2, and 3)
- **Fix: Upgrade to PAYG** (see Mitigation section above) — enables multi-region subscription
