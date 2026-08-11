# OCI CLI Setup — API Key Configuration

## What You Need

From the Oracle Cloud Console, collect:
- **Private RSA key** — generated via Console (Profile → API Keys → Add API Key)
- **Fingerprint** — shown after adding the key (e.g., `39:5e:ea:18:bf:47:85:7c:55:54:da:04:e7:8b:ed:47`)
- **User OCID** — from Profile page (e.g., `ocid1.user.oc1..aaaaaaaan7xf3zyuq...`)
- **Tenancy OCID** — from Tenancy page under Governance (e.g., `ocid1.tenancy.oc1..aaaaaaaai3iezjhs...`)
- **Region** — e.g., `us-ashburn-1` (IAD)

## File Layout

```
~/.oci/
  ├── config          # [DEFAULT] section with all OCIDs
  └── oci_api_key.pem # Private RSA key (keep secret, 0600 permissions)
```

### ~/.oci/config
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaan7xf3zyuq5ytczltk5egla3stjlthahtyhasdybpzeam2pe7xq7a
fingerprint=39:5e:ea:18:bf:47:85:7c:55:54:da:04:e7:8b:ed:47
tenancy=ocid1.tenancy.oc1..aaaaaaaai3iezjhsbdiujo5oo372uttqjhufsh5uaphxlkjgjiamzjwijgda
region=us-ashburn-1
key_file=~/.oci/oci_api_key.pem
```

### ~/.oci/oci_api_key.pem
```
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSj...
...
-----END PRIVATE KEY-----
```

## Verification

```bash
# Suppress Windows permission warnings
export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True
export SUPPRESS_LABEL_WARNING=True

# Test connectivity
oci iam availability-domain list

# Expected output — shows 3 ADs in Ashburn:
# {
#   "data": [
#     { "name": "zRUb:US-ASHBURN-AD-1" },
#     { "name": "zRUb:US-ASHBURN-AD-2" },
#     { "name": "zRUb:US-ASHBURN-AD-3" }
#   ]
# }

# List regions
oci iam region list
```

## Verification via Python

```python
from oci.config import from_file
from oci.core import ComputeClient
from oci.identity import IdentityClient

config = from_file()
identity = IdentityClient(config)
ads = identity.list_availability_domains(config['tenancy']).data
for ad in ads:
    print(ad.name)  # zRUb:US-ASHBURN-AD-1, -AD-2, -AD-3
```

## Permission Warnings on Windows

OCI CLI warns that `~/.oci/config` and `~/.oci/oci_api_key.pem` have too-permissive ACLs on Windows (non-admin users/groups with read access). Two options:

1. **Supress warnings** (safe if you're the only user on the machine):
   ```bash
   export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True
   export SUPPRESS_LABEL_WARNING=True
   ```

2. **Fix permissions** (proper but complex on Windows):
   ```bash
   oci setup repair-file-permissions --file ~/.oci/config
   oci setup repair-file-permissions --file ~/.oci/oci_api_key.pem
   ```

On Windows with git-bash, the `repair-file-permissions` command may not work correctly (it uses POSIX chmod which doesn't translate cleanly to Windows ACLs). The suppress approach is more reliable.

## Common OCI CLI Patterns

### List availability domains
```bash
oci iam availability-domain list
```

### List VCNs in root compartment
```bash
oci network vcn list --compartment-id "$tenancy_ocid" --all
```

### Launch a compute instance (VM.Standard.E2.1.Micro — Always Free)
```bash
oci compute instance launch \
  --compartment-id "$tenancy_ocid" \
  --availability-domain "zRUb:US-ASHBURN-AD-1" \
  --display-name "chesapeake-vps" \
  --image-id "ocid1.image.oc1.iad.aaaaaaaaioyy7je3vndsccly24frkfptl5lggvyupubg74awcf2gmua7k3ra" \
  --shape "VM.Standard.E2.1.Micro" \
  --subnet-id "$subnet_ocid" \
  --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
  --assign-public-ip true
```

### Get public IP of a running instance
```bash
oci compute instance list-vnics \
  --compartment-id "$tenancy_ocid" \
  --instance-id "$instance_ocid" \
  --query "data[0].\"public-ip\"" --raw-output
```

## OCI Python SDK Quick Install

```bash
pip install oci
```

The `oci` CLI should be in the same venv as the SDK. If installed globally, it's at:
```
~/AppData/Local/Programs/Python/Python311/Scripts/oci
```

## Pitfalls

- **Empty VCN list for new accounts** — A brand-new Oracle Free Tier account has NO VCNs by default. You must create one (via Console or CLI) before you can launch instances.
- **Two firewalls** — Oracle has VCN security lists (cloud firewall) AND instance iptables (OS firewall). Both must allow traffic. VCN security list is the more common blocker.
- **"Out of host capacity"** — Ampere A1 shapes frequently return this in Ashburn. VM.Standard.E2.1.Micro is more reliable. See `references/oci-ammpere-retry-patterns.md`.
- **Single region limit** — Free tier accounts can only subscribe to one region (the home region selected at signup). You cannot switch without upgrading to PAYG.
- **Config file format** — `key_file` path uses `~` which OCI CLI resolves. On Windows with git-bash, use the full POSIX path (`${USER_HOME}/.oci/oci_api_key.pem`) if `~` doesn't resolve.
