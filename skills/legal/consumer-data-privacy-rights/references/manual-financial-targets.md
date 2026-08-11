# Manual Financial/Identity Targets

> These services hold critical identity and financial data but do NOT appear in any of the three open-source data broker datasets (Optery, PersProtect, OptOutRights). They must be added manually to any privacy pipeline.

## Service Table

| Service | Website | Contact Email | What They Hold | FCRA Applicable |
|---------|---------|---------------|---------------|-----------------|
| ChexSystems | https://www.chexsystems.com | consumerdept@chexsystems.com | Banking history — closed accounts, bounced checks, fraud reports | ✅ Yes |
| Early Warning Services (Zelle) | https://www.earlywarning.com | privacy@earlywarning.com | Shared banking intelligence among major US banks (BOA, Chase, Wells Fargo), Zelle transaction history | ✅ Yes |
| TeleCheck | https://www.firstdata.com (FIS) | privacy@fisglobal.com | Check writing verification history | ✅ Yes |
| Certegy | https://www.certegy.com | privacy@certegy.com | Check verification services | ✅ Yes |
| MIB Group (Medical Information Bureau) | https://www.mib.com | privacy@mib.com | Medical underwriting data used by life/health insurers | ✅ Yes |
| Milliman IntelliScript | https://www.milliman.com | privacy@milliman.com | Prescription drug history used by life insurers for risk assessment | Partial |
| Verisk / ISO (Insurance Services Office) | https://www.verisk.com | privacy@verisk.com | Insurance claims history (CLUE reports — Comprehensive Loss Underwriting Exchange) | ✅ Yes |
| CoreLogic | https://www.corelogic.com | privacy@corelogic.com | Property records, rental history, credit-risk data | Partial |
| ARIS (Advanced Resolution Information Services) | https://www.aris.com | privacy@aris.com | Tenant screening and rental history | ✅ Yes |

## FCRA Consumer Disclosure Process

Many of these services are subject to the Fair Credit Reporting Act (FCRA), which means:
- You are entitled to **one free consumer disclosure every 12 months**
- The disclosure must include **all information** in your file
- You also have the right to dispute inaccuracies and request deletion

**Process for FCRA-governed services:**

1. **Freeze your file first** — prevents new inquiries during processing
2. **Request consumer disclosure** — this is the FCRA term for what CCPA calls a DSAR
3. **Review the data** — check for errors, outdated info, unauthorized reporting
4. **Dispute inaccuracies** — FCRA § 611 requires investigation within 30 days
5. **Request deletion** — CCPA provides deletion rights even for FCRA-governed entities (though some data may be exempt due to legal retention requirements)

## Sample Letter for ChexSystems

```
[DATE]

VIA EMAIL: consumerdept@chexsystems.com
VIA CERTIFIED MAIL RETURN RECEIPT REQUESTED

ChexSystems
Attn: Consumer Disclosure Department
[ADDRESS FROM WEBSITE]

RE: CONSUMER DISCLOSURE REQUEST UNDER FCRA § 609 (15 U.S.C. § 1681g)
    AND DATA SUBJECT ACCESS REQUEST UNDER CCPA/CPRA

To Whom It May Concern:

I am a California resident and I am requesting my consumer disclosure file
as provided for under the Fair Credit Reporting Act (15 U.S.C. § 1681g)
together with the California Consumer Privacy Act.

Please provide me with a complete copy of my consumer file, including:
1. All information in my file at the time of the request
2. The sources of the information
3. A list of everyone who has accessed my file in the past 2 years
4. Any adverse actions or fraud alerts on file

Identification:
- Full Name: [NAME]
- Date of Birth: [DOB]
- Current Address: [ADDRESS]
- Previous Addresses (last 5 years): [ADDRESSES]
- Phone Number: [PHONE]
- SSN (last 4 digits only): [XXXX]

Please provide the disclosure in writing via mail and, if available,
in electronic format (PDF). I also request deletion of my personal
information per my CCPA rights upon delivery of the disclosure.

Sincerely,
[NAME]
```

> Note: ChexSystems and Early Warning do NOT accept consumer disclosure requests via email — you must submit via their web portals or mail. The email addresses above are for privacy policy inquiries. Actual disclosure requests should go through their dedicated consumer portals.
