# Gowanus Kettle Brewing Co. (synthetic demo business)

**Everything in this folder is made up.** Gowanus Kettle Brewing Co. LLC is a fictional Brooklyn microbrewery and
taproom created for the moneyfinder demo. It is not a real business; no real person, account or filing is described.

| Item | Synthetic value | Why it is safe |
|---|---|---|
| Domain | `gowanuskettle.example` | `.example` is reserved (RFC 2606) and can never resolve to a real site. Only `normalize_stored` (stored-data lookups) accepts it; signup and `company-research` still reject it, so no collector ever runs against it. |
| EIN | `00-4271985` | The `00` prefix is never issued by the IRS. |
| NY DOS id | `9990142` | Made up. |
| Phone | `(718) 555-0142` | 555-01xx numbers are reserved for fiction. |
| People | Marisol Vance (Managing Member), Darnell Reyes, Keisha Monroe, Owen Halloran CPA, Priya Shah | Fictional. Email addresses use `.example` domains. |

The story: NAICS 312120 brewery at 417 Sackett Street, Brooklyn (Kings County), LLC formed in New York in 2019,
14 employees at the end of 2025, payroll on Gusto, small-group health plan through the NY State of Health
marketplace, a SIMPLE IRA started in 2025, two veterans hired in 2025 (WOTC paperwork, DD-214s), a $186,500
canning line financed and placed in service in July 2025, 38 kW rooftop solar, an EV charger and an AED in the taproom,
and about 3,100 barrels brewed in New York in 2025. The accountant is preparing the 2025 IT-204 with IT-636, IT-212,
IT-643 and Form 8941.

## Files

- `profile.json`: research/company profile format. Every claim's source is `demo:synthetic` (the `via` names the
  collector it stands in for, which sets the dossier's `source_kind`: registry, enrichment, web or llm).
- `business.json`: signup answers (domain, name, contact email, officer name and title, tax year), `demo: true`.
- `inbox.jsonl`: 25 synthetic emails in `store.read_messages` format (Gusto payroll, Indeed hires, NYS DTF, NYS DOL
  WOTC, SLA, TTB, Chase equipment financing, Con Edison solar, Oscar health plan, broker and accountant threads).
  Message ids are `synthetic-gk-NNN`; sender domains of real providers are used only so the category rules apply.

## Use

```
make demo-seed          # copy into the git-ignored data dirs, build the dossier (Bedrock reads the synthetic inbox),
                        # push it to SurrealDB Cloud. NO_LLM=1 skips Bedrock, NO_PUSH=1 skips SurrealDB.
make dossier-get SLUG=gowanuskettle-example
make demo               # then open http://localhost:8000/companies/gowanuskettle.example
```

The profile also carries a synthetic NY unclaimed-funds record (Con Edison utility deposit refund, $1,284.36) so the
mock claim portal fills completely.
