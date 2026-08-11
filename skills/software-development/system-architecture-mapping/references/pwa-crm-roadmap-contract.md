# PWA ↔ CRM Roadmap Contract Reference

## Investigation checklist

Before planning a cross-repository PWA/CRM build, record actual values—not assumptions—for:

- PWA routes, auth roles, local models, adapter modules, and existing docs.
- Live CRM workspace ID, schema, record counts, custom fields, assignment relation, RLS/feature flags, and integration-secret presence (presence only; never values).
- Source lead assets and row/column counts without dumping PII.
- Repository ownership and canonical locations for billing, onboarding, CRM, pitch pages, and commissions.

## Document family

Save a numbered Markdown family under the implementation repository:

- `00_MASTER_*_ROADMAP.md`: executive recommendation, findings, target architecture, phases, risks, gates.
- `01_PHASE1_*`: data model/import.
- `02_PHASE2_*`: assignment/access control and CRM projection.
- `03_PHASE3_*`: operator UX and activity sync.
- `09_SYSTEM_IMPACT_*`: ownership, data flow, system impact, env/security contract.
- `10_*_INTEGRATION_CONTRACT.md`: stable IDs, event envelope, directionality, failure policy.

The master document should separate **verified current state** from **proposed future state**.

## Recommended integration contract

```text
Source lead asset → PWA import → CRM Company projection
PWA assignment ─────────────────→ CRM native owner relation
PWA activity ───────────────────→ CRM notes/stages/tasks via idempotent adapter
CRM manager changes ────────────→ PWA only through explicit reconciliation policy
Billing/commission ─────────────→ canonical product/billing repository
```

Every event should carry:

- stable event/idempotency key
- local PWA lead ID
- optional CRM record IDs
- authenticated actor ID
- CRM workspace-member ID where relevant
- schema/payload version
- timestamp

Never include passwords, JWTs, API keys, SSNs, bank details, Stripe KYC payloads, or full tax forms.

## Security and correctness rules

- Enforce VA assignment scope in the PWA backend before serialization; never client-filter a full lead pool.
- Project assignment to the CRM's native relation only after validating the workspace-member mapping.
- Treat CRM filtered views as UX, not security.
- Test CRM isolation across the record graph (companies, people, opportunities, notes, activities, tasks, relations), not only the primary list.
- Write local activity state before external sync; expose `pending_sync`/`failed_sync`; retry with the same idempotency key.
- Prefer additive domain models when the new product workflow has a distinct lifecycle from a legacy generic Company model.
- Pilot with one operator and 10–50 records before enabling a full source batch.

## Validation and delivery

Validate Markdown/diffs and count saved files. Then commit and push the documentation family. Report exact findings, exact artifact paths, commit/push status, and any unresolved risks. Do not claim a live integration was completed merely because a plan or API key exists.
