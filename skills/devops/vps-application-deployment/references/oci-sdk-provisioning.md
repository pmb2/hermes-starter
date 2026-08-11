# OCI SDK Provisioning — Python Reference

Full Python SDK commands for managing Oracle Cloud Infrastructure (OCI) compute instances.

## Setup

```bash
pip install oci  # or: /path/to/python -m pip install oci
```

OCI config at `~/.oci/config`:
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaa...
tenancy=ocid1.tenancy.oc1..aaaa...
region=us-ashburn-1
key_file=${USER_HOME}\.oci\oci_api_key.pem
fingerprint=15:dd:a2:9d:...
```

## List Existing Instances

```python
import oci
from oci.config import from_file
from oci.core import ComputeClient, VirtualNetworkClient

config = from_file()
compute = ComputeClient(config)
vcn = VirtualNetworkClient(config)

instances = compute.list_instances(config['tenancy'])
for inst in instances.data:
    print(f"{inst.display_name}: {inst.shape} ({inst.lifecycle_state})")
```

## Get Instance IPs

```python
# After listing instances, for each:
vnics = compute.list_vnic_attachments(config['tenancy'], instance_id=inst.id)
for va in vnics.data:
    vnic = vcn.get_vnic(va.vnic_id)
    print(f"  Public: {vnic.data.public_ip}")
    print(f"  Private: {vnic.data.private_ip}")
```

## Launch Ampere A1 Instance

```python
import oci
from oci.config import from_file
from oci.core import ComputeClient, VirtualNetworkClient
from oci.core.models import (
    LaunchInstanceDetails,
    InstanceSourceViaImageDetails,
    LaunchInstanceShapeConfigDetails,
    CreateVnicDetails,
)

config = from_file()
compute = ComputeClient(config)
vcn = VirtualNetworkClient(config)

# SSH key
with open('/path/to/.ssh/key.pub') as f:
    ssh_key = f.read().strip()

# Find Ubuntu ARM image
images = compute.list_images(config['tenancy'], limit=200, operating_system='Canonical Ubuntu')
# Pick the latest aarch64 image
image_id = [i for i in images.data if 'aarch64' in i.display_name][0].id

# Find subnet (reuse existing VCN)
vcns = vcn.list_vcns(config['tenancy'])
# Pick your VCN, then pick a public subnet
subnet_id = vcn.list_subnets(config['tenancy'], vcn_id=vcns.data[0].id).data[0].id

# Get availability domain
from oci.identity import IdentityClient
ad = IdentityClient(config).list_availability_domains(config['tenancy']).data[0].name

# Launch
details = LaunchInstanceDetails()
details.compartment_id = config['tenancy']
details.display_name = 'my-instance'
details.shape = 'VM.Standard.A1.Flex'
details.availability_domain = ad

sc = LaunchInstanceShapeConfigDetails()
sc.ocpus = 2          # up to 4 for free tier
sc.memory_in_gbs = 12 # up to 24
details.shape_config = sc

src = InstanceSourceViaImageDetails()
src.image_id = image_id
details.source_details = src

vnic = CreateVnicDetails()
vnic.subnet_id = subnet_id
vnic.assign_public_ip = True
details.create_vnic_details = vnic

details.metadata = {'ssh_authorized_keys': ssh_key}
details.freeform_tags = {'Project': 'MyApp'}

response = compute.launch_instance(details)
instance = response.data
print(f"OCID: {instance.id}")

# Poll for RUNNING
import time
for _ in range(20):
    d = compute.get_instance(instance.id)
    if d.data.lifecycle_state == 'RUNNING':
        vnics = compute.list_vnic_attachments(config['tenancy'], instance_id=instance.id)
        for va in vnics.data:
            v = vcn.get_vnic(va.vnic_id)
            print(f"IP: {v.data.public_ip}")
        break
    time.sleep(15)
```

## Check Available Shapes

```python
shapes = compute.list_shapes(config['tenancy'], limit=100)
for s in shapes.data:
    if 'A1' in s.shape or 'E2' in s.shape:
        print(s.shape)
```

## Security List Management

```python
# List VCNs
vcns = vcn.list_vcns(config['tenancy'])
for v in vcns.data:
    print(f"{v.display_name}: {v.cidr_block}")
    subnets = vcn.list_subnets(config['tenancy'], vcn_id=v.id)
    for sn in subnets.data:
        print(f"  Subnet: {sn.display_name} ({sn.cidr_block})")
    sec_lists = vcn.list_security_lists(config['tenancy'], vcn_id=v.id)
    for sl in sec_lists.data:
        print(f"  SecList: {sl.display_name}")
        for rule in sl.ingress_security_rules:
            if rule.protocol == '6':  # TCP
                ports = ''
                if rule.tcp_options and rule.tcp_options.destination_port_range:
                    pr = rule.tcp_options.destination_port_range
                    ports = f'ports={pr.min}-{pr.max}'
                print(f"    INGRESS {rule.source} {ports}")
```

## Known OCIDs (us-ashburn-1)

| Resource | OCID |
|----------|------|
| hamilton-vcn subnet | ocid1.subnet.oc1.iad.aaaaaaaaaoj3npr5xkslffj3otcyxq7pzsx4t4gwzsl7x6hgsex4w5vn6d3q |
| Ubuntu 24.04 aarch64 (2026.04.30) | ocid1.image.oc1.iad.aaaaaaaaioyy7je3vndsccly24frkfptl5lggvyupubg74awcf2gmua7k3ra |
| AD-1 | oRwF:US-ASHBURN-AD-1 |
| AD-2 | oRwF:US-ASHBURN-AD-2 |
| AD-3 | oRwF:US-ASHBURN-AD-3 |
