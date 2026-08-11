# Shared Multi-Repo Feature Delivery — Session Reference

## Proven patterns

### Ownership mapping

When Website Landlord and GHL both participate in salesperson payments:

- Website Landlord owns customer billing, fulfillment lifecycle, commission economics, agreement/product planning, and the canonical cross-repo map.
- GHL `leads/company-crm-pwa` owns the live partner register, FOSS signing, document evidence, Twenty provisioning, and the live Connect checklist.
- Add reciprocal pointers in both repos; link the detailed map instead of duplicating it.

### Dynamic tax-track contract

Use checklist metadata with `audience: us|foreign|both` and derive the track server-side.

Verified track IDs from the session:

- US: `w9`, `contractor-1099`, shared agreements, `stripe-connect-express`
- Foreign: `w8ben`, `foreign-contractor-ack`, shared agreements, `stripe-connect-express`

Required behavior:

- `GET /public/sales-onboarding/checklist?citizenship=us|foreign`
- `GET /public/sales-onboarding/documents/status?email=...&citizenship=...`
- document submissions include `citizenship`; foreign submissions include country/tax-country
- account completion requires citizenship and foreign tax country when applicable
- backend rejects documents whose audience does not match the selected track

### Hosted Connect status

- Start Express onboarding with the selected track/country metadata.
- Preserve `citizenship` on Stripe return/refresh URLs.
- Poll status from the register page approximately every 8 seconds while active.
- Stop polling when `ready_for_commission` is reached or when the page is destroyed.
- Do not expose a manual Refresh button when automatic status is requested.

### Deployment evidence

The session demonstrated an important reporting distinction: backend/frontend builds and API contract checks passed, and commits were pushed, but the final Docker deployment was blocked when the Docker Desktop engine became unavailable. The correct report is “committed and pushed; deployment blocked,” not “deployed.”

For future work, after Docker returns, rebuild from committed sources and verify both checklist API variants plus browser UI. A hot patch is not durable deployment.

## Compliance boundary

W-8BEN-style internal capture and country-dependent Connect setup require attorney/accountant review before treating them as production tax/legal workflows. Do not represent internal generated forms as official IRS forms without approved templates and review.
