# Oracle Cloud Free Tier VPS Provisioning

## Prerequisites
- Oracle Cloud account (created by the client/project owner)
- OCI API key configured in `~/.oci/config`
- SSH key pair created

## OCI Config File
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaa...
tenancy=ocid1.tenancy.oc1..aaaaaaaa...
region=us-ashburn-1
key_file=${USER_HOME}\.oci\oci_api_key.pem
fingerprint=15:dd:a2:9d:...
```

## SDK Setup
```bash
pip install oci
```

## Check Existing Instances
```python
from oci.config import from_file
from oci.core import ComputeClient, VirtualNetworkClient

config = from_file()
compute = ComputeClient(config)

instances = compute.list_instances(config['tenancy'])
for inst in instances.data:
    print(f"{inst.display_name}: {inst.shape} ({inst.lifecycle_state})")
    vcn = VirtualNetworkClient(config)
    vnics = compute.list_vnic_attachments(config['tenancy'], instance_id=inst.id)
    for attach in vnics.data:
        nic = vcn.get_vnic(attach.vnic_id)
        print(f"  IP: {nic.data.public_ip}")
```

## Available Images (Ubuntu ARM64)
```python
images = compute.list_images(config['tenancy'], operating_system='Canonical Ubuntu')
for img in images.data:
    if '24.04' in img.display_name and 'aarch64' in img.display_name:
        print(f"{img.display_name}: {img.id}")
```

## Available Shapes
```python
shapes = compute.list_shapes(config['tenancy'])
for s in shapes.data:
    if 'A1.Flex' in s.shape or 'E2.1.Micro' in s.shape:
        print(s.shape)
```

## Launch Instance
See main SKILL.md for the full launch pattern.

## Get Public IP After Provisioning
```python
import time

for i in range(20):
    detail = compute.get_instance(instance_id)
    if detail.data.lifecycle_state == 'RUNNING':
        vnics = compute.list_vnic_attachments(config['tenancy'], instance_id=instance_id)
        for attach in vnics.data:
            vnic = vcn.get_vnic(attach.vnic_id)
            print(f"Public IP: {vnic.data.public_ip}")
        break
    time.sleep(15)
```

## 🔄 Instance Cleanup

When an instance is created on the wrong account or needs to be destroyed:

```python
from oci.config import from_file
from oci.core import ComputeClient

config = from_file()
compute = ComputeClient(config)

# Terminate and delete boot volume
compute.terminate_instance('<instance-ocid>', preserve_boot_volume=False)
print('Instance terminated.')
```

## ⚠️ OCI SDK Gotchas

### `CannotParseRequest` (400 Error)
If `compute.launch_instance()` returns a 400 `CannotParseRequest`, the SDK model constructors may not match the API version. **Fix:** Create model objects with empty constructors and set attributes individually:

```python
# ❌ WRONG — may fail with CannotParseRequest
launch = LaunchInstanceDetails(
    display_name='myapp',
    shape='VM.Standard.A1.Flex',
    shape_config=ShapeConfig(ocpus=2, memory_in_gbs=12),  # ShapeConfig may not exist
    assign_public_ip=True,  # Not a valid kwarg
    ...
)

# ✅ CORRECT — set attributes individually
from oci.core.models import LaunchInstanceDetails, InstanceSourceViaImageDetails, LaunchInstanceShapeConfigDetails, CreateVnicDetails

details = LaunchInstanceDetails()
details.compartment_id = config['tenancy']
details.display_name = 'myapp'
details.shape = 'VM.Standard.A1.Flex'
details.availability_domain = 'oRwF:US-ASHBURN-AD-1'

shape = LaunchInstanceShapeConfigDetails()
shape.ocpus = 2
shape.memory_in_gbs = 12
details.shape_config = shape

source = InstanceSourceViaImageDetails()
source.image_id = '<image-ocid>'
details.source_details = source

vnic = CreateVnicDetails()
vnic.subnet_id = '<subnet-ocid>'
vnic.assign_public_ip = True
details.create_vnic_details = vnic

details.metadata = {'ssh_authorized_keys': ssh_key}
```

### Class Name Mismatches by SDK Version
- `ShapeConfig` → `LaunchInstanceShapeConfigDetails` (class name varies by OCI SDK version)
- `assign_public_ip` is NOT a kwarg of `LaunchInstanceDetails` — must use `CreateVnicDetails`
- `source_details` accepts `InstanceSourceViaImageDetails` (not a bare dict)

### `list_images` Only Returns Windows Images
If `compute.list_images()` only returns Windows images, filter by operating system:

```python
images = compute.list_images(config['tenancy'], operating_system='Canonical Ubuntu')
```

### Limit Checking
To check available Ampere A1 capacity:
```python
limits = limits_client.list_limit_values(config['tenancy'], 'compute', limit=100)
for l in limits.data:
    if 'a1' in l.name.lower() or 'micro' in l.name.lower():
        print(f'{l.name}: val={l.value} scope={l.scope_type}')
```

## 🔁 ARM "Out of Host Capacity" Retry

Oracle free-tier ARM (Ampere A1) instances frequently hit **"Out of host capacity"** due to oversubscription, especially in US East (Ashburn). All three ADs may fail simultaneously. This is normal — the only fix is persistent retry.

### Retry Strategy
- **Retry every 15 minutes** — capacity opens when other users release instances
- **Try all 3 ADs** in each cycle (AD-1, AD-2, AD-3)
- **Early morning / late night US time** has highest success rates
- **Plan for 1-48 hours** of retries in contested regions

### OCI CLI Retry Pattern (bash, no_agent=true cron)
```bash
#!/bin/bash
# arm-provision-retry.sh — try all 3 ADs per cycle
export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True

for AD in "oRwF:US-ASHBURN-AD-1" "oRwF:US-ASHBURN-AD-2" "oRwF:US-ASHBURN-AD-3"; do
    OUTPUT=$(oci compute instance launch \
        --compartment-id <tenancy-ocid> \
        --availability-domain "$AD" \
        --display-name spacebar-arm \
        --shape VM.Standard.A1.Flex \
        --shape-config '{"ocpus":"2","memory-in-gbs":"12"}' \
        --subnet-id <subnet-ocid> \
        --assign-public-ip true \
        --image-id <ubuntu-arm-ocid> \
        --ssh-authorized-keys-file ~/.ssh/key.pub 2>&1)
    if grep -q "PROVISIONING" <<< "$OUTPUT"; then echo "SUCCESS"; exit 0; fi
done
exit 1  # All ADs full — retry next cycle
```

Schedule via Hermes cron: `cronjob(action='create', schedule='every 15m', script='arm-provision-retry.sh', no_agent=true, deliver='local')`.

### Oracle Free Tier Limits (Per Account)
| Resource | Limit | Notes |
|----------|-------|-------|
| ARM Ampere A1 cores | 4 OCPU max | Split across up to 4 instances |
| ARM Ampere A1 RAM | 24 GB max | Proportional (6GB per OCPU) |
| AMD micro instances | 2 max | VM.Standard.E2.1.Micro, ~1GB each |
| Boot volume (total) | 200 GB | Shared across all instances |
| Block storage | 100 GB free | Additional volumes |
| Outbound data | 10 TB/month | Internet egress |
| **Signup requirements** | Email + Phone (SMS) + Credit Card | CC is ID verification only — not charged on free tier |

### Multi-Account Constraints
Each Oracle account needs a **unique phone number** for SMS verification — this is the main bottleneck. Virtual numbers (Google Voice, TextNow) are often rejected. Best approach is to maximize a single account's free tier (4 ARM cores + 2 AMD micros = 6 VMs) rather than splitting across multiple accounts.

### OCI CLI Quick Reference
```bash
# Suppress file permission warnings
export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True

# List running instances
oci compute instance list --compartment-id <tenancy-ocid> --all

# Launch instance
oci compute instance launch --compartment-id <tenancy-ocid> \
    --availability-domain oRwF:US-ASHBURN-AD-1 \
    --display-name my-node --shape VM.Standard.A1.Flex \
    --shape-config '{"ocpus":"2","memory-in-gbs":"12"}' \
    --subnet-id <subnet-ocid> --assign-public-ip true \
    --image-id <ubuntu-arm-ocid> --ssh-authorized-keys-file ~/.ssh/key.pub

# Get public IP
oci compute instance list-vnics --instance-id <ocid> --all

# Terminate
oci compute instance terminate --instance-id <ocid> --preserve-boot-volume false

Pitfall: OCI CLI emits stdout file-permission warnings that break JSON parsing. Always set OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True and pipe through grep -v "^WARNING:" when piping to jq/python/json.tool.
```
