# Client Onboarding System — Agency SOP Reference

The core strategic model: transition from "freelancer manually setting up infrastructure" to "agency with standardized client onboarding." SOPs make every new client the same repeatable pipeline instead of a bespoke project.

## The Client Pipeline

```
Lead → Proposal → Deposit → Client Onboarding → Accounts Created → Credentials Collected → Infrastructure Provisioned → Deployment → Testing → Handoff → Maintenance/Support
```

## Client-Owned Accounts Model

| Service | Who Owns | Agency Gets |
|---------|----------|-------------|
| Domain registrar | Client | Admin/delegated access |
| Twilio | Client | API keys |
| Oracle Cloud (or hosting) | Client (or agency for small projects) | Technical admin access |
| Cloudflare | Client | DNS access |
| Google Workspace | Client | Admin access (optional) |
| Stripe | Client | Connected account access |

## SOP Documents (Markdown, convert to PDF for delivery)

### 1. Domain Setup SOP
- Buy a domain (Namecheap recommended)
- Set up Cloudflare for DNS
- Delegate DNS to Cloudflare (change nameservers)
- Add agency as admin user on the registrar account
- Add A record pointing to VPS IP

### 2. Oracle Cloud VPS SOP
- Create Oracle Cloud account (new email if client doesn't have one)
- Verify payment method (credit card — no charge on free tier)
- Request service limit increase for ARM compute (if needed)
- Enable ARM Ampere A1 instances in US-ASHBURN-1 region
- Add your SSH public key
- Create VCN with public subnet + security list (ports 22, 80, 443)
- Launch instance (Ubuntu 24.04 ARM64, VM.Standard.A1.Flex)
- Add your email as admin on the account
- Document: instance IP, SSH key path, OCI config file

### 3. Twilio SOP
- Sign up at twilio.com
- Complete identity verification (phone, government ID if needed)
- Add payment method (prepay or credit card)
- Buy a phone number (~$1-5/mo)
- Invite agency as admin on the project
- Enable A2P 10DLC if sending SMS in US (brand registration required)
- Generate API keys (Account SID + Auth Token)
- Set up webhook URLs for incoming messages/calls

### 4. Deployment Handoff SOP
- Project production URL
- Admin login credentials
- Stack documentation (Docker services, ports, volumes)
- Maintenance procedures (backup, restart, update)
- Support boundaries (what you handle vs what they handle)
- Uptime expectations (no SLA on free tier)
- Emergency contact procedure

## Recommended Agency Folder Structure

For storing internal SOPs and client-facing docs:

```
/agency/
  /SOPs/
    domain-setup.md
    oracle-cloud-vps.md
    twilio-setup.md
    deployment-handoff.md
  /client-templates/
    onboarding-packet.md
    support-policy.md
    cost-expectations.md
  /deployment-checklists/
    vps-checklist.md
    pre-launch-checklist.md
  /handoff-docs/
    README-template.md
    credentials-template.md
```

## Client-Facing Packet Structure

For delivering to clients:

```
/client-onboarding-packet/
  README.md                    — Overview, what to expect, timeline
  domain-setup-instructions.md — Step-by-step domain purchase + DNS
  oracle-setup-instructions.md — Account creation guide
  twilio-setup-instructions.md — Twilio signup + payment guide
  cost-expectations.md         — What it costs (domains ~$10-20/yr, Twilio ~$1-5/mo, hosting free)
  support-policy.md            — What's covered, response times, escalation
```

## Key Principles

- **Do NOT customize per client.** Standardize: same stack, same deployment model, same proxy, same DNS provider, same onboarding, same handoff. Variability destroys velocity.
- **Version 1:** Markdown docs. After 5-10 clients, automate further. Don't build a fancy portal yet.
- **Domains, Twilio, and payment methods should ideally be client-owned.** This avoids service-hostage optics, funding interruptions, and billing nightmares.
- **You maintain technical admin access** on everything. Client owns billing. Agency owns operations.
- **Operational consistency first, polish second.**
