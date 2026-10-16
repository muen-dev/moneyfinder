# Form filler handoff: where a business's data lives

Every researched business has one **dossier** (`schema: moneyfinder.dossier/v1`). Fill forms from it; never from raw scraper output.

**Demo business:** Gowanus Kettle Brewing Co. LLC (`gowanuskettle.example`, slug `gowanuskettle-example`) is synthetic and complete: `missing_info` is empty, EIN `00-4271985` (the IRS never issues the `00` prefix), officer Marisol Vance, tax year 2025. Good first forms: NYS beer production credit (`nys_beer_prod`, CT-636), hire-a-veteran (`nys_hire_a_veteran`, DTF-75 / CT-643), federal small-employer health (8941). `make demo-seed` rebuilds it from `demo/gowanus-kettle/` and pushes it to SurrealDB.

## Getting it (any one of these)

| Where | How |
|---|---|
| SurrealDB Cloud (ns `moneyfinder`, db `main`) | `RETURN fn::business_dossier('gowanuskettle-example');` (or `make dossier-get SLUG=gowanuskettle-example`). Returns `{slug, business, record, missing_info, email_signals, facts, credits, claimed}`; `business` is `NONE` for an unknown slug. Full JSON: `RETURN type::record('business', 'gowanuskettle-example').dossier;` |
| Web app (`make demo`) | `GET /companies/<domain>/dossier.json`, or `/businesses/<business_id>/dossier.json` for a Gmail-connected business. `?refresh=1` rebuilds it. |
| File | `research/company/data/<domain>/dossier.json`, `research/business/data/<business_id>/dossier.json` |

The **slug** is the dossier's `slug` field (the domain with non-alphanumerics as `-`, e.g. `gowanuskettle-example`; a connected business without a domain uses its business id). Refresh: `make dossier DOMAIN=<domain>` then `make dossier-push ID=<domain>`.

## Fields

`business` holds the single best value per key, with the same keys in all three sources (precedence user > registry > enrichment > web > email > llm, then confidence). In SurrealDB, `record` adds the kb's typed copies (`entity_type` normalized, `employees` as int or `NONE`). `facts` holds **every** observed value with `source` (URL / registry / message id), `source_kind` (`web|registry|enrichment|email|llm|user`), `confidence` 0-1 and `captured_at`: show these as provenance next to each filled value. `credits` are matched programs (`id`, `name`, `jurisdiction`, `status` likely/possible, `reasons`, `forms[{code, title, url}]`, `tax_year`).

| Form field | `business.<key>` | Notes |
|---|---|---|
| Legal name | `legal_name` | NY DOS registry name when available. `name` is the display/brand name, `dba` the assumed name. |
| EIN / FEIN | `ein` | Usually missing (not public). Show masked `**-***1234`; never log it. |
| Address | `hq_address`, `county`, `nyc_borough` | One-line string; split into street/city/ZIP yourself, don't invent missing parts. |
| NAICS | `naics[0]` | List of 6-digit strings, best first; `industry` is the label. |
| Entity type | `entity_type` | Raw registry text (e.g. "Domestic Limited Liability Company"); `record.entity_type` is one of `c_corp s_corp partnership llc sole_prop nonprofit`. |
| State of formation / DOS ID | `state_of_formation`, `ny_dos_id` | From NY DOS. |
| Employees | `employees` | May be text like "3 employees on LinkedIn" (`record.employees` is then `NONE`); forms want a payroll count, so confirm with the user. |
| Officer name / title | `officer_name`, `officer_title` | From signup answers (business.json) or mail; otherwise in `missing_info`. |
| Tax year | `tax_year`, else credit's `tax_year` | `business.tax_year` when the owner gave it; credits default to last calendar year; confirm with the user. |
| Phone / email / payroll | `phone`, `contact_email`, `payroll_provider` | `payroll_provider` comes from email signals. |

## `missing_info`

Keys a credit form needs that no source provided (e.g. `ein`, `officer_name`, `tax_year`). **Ask the user for each one in the product UI and never guess, derive or leave a placeholder.** A field that is missing and that the user did not supply stays blank and the form is not submitted. Answers the user types are new facts with `source_kind: "user"`.

## Writing results back (SurrealDB)

A user's answer is a fact. The unique index on business + key + value + source makes a retry harmless:

```sql
CREATE fact CONTENT { business: business:`gowanuskettle-example`, key: 'officer_title', value: 'Managing Member',
                      source: 'user', source_kind: 'user', confidence: 1.0 };
```

A filled or filed form is a `claimed` edge from the business to the credit (one per tax year). `status` is `drafted | filed | accepted | paid | denied`, and `form` is `form:['<code>', <tax_year>]`:

```sql
RELATE business:`gowanuskettle-example` -> claimed -> incentive:nys_beer_prod
    CONTENT { tax_year: 2025, status: 'drafted', form: form:['CT-636', 2025] };
```

`fn::business_dossier` returns these under `claimed`. `make dossier-push` rewrites only a business's non-user facts from its dossier file, so answers saved with `source_kind: 'user'` survive it, and the web app pushes each dossier it builds or rebuilds to SurrealDB in the background (off with `KB_AUTO_PUSH=0`).

## Safety (from `docs/DAYTONA_BROWSER_SAFETY.md`)

Demo mode navigates only to the mock portal (host allowlist: mock portal origin only for submission) and fills only fields on the approved form snapshot, skipping any marked `requires_confirmation`. After filling, read DOM values back and diff them against the approved values; on any mismatch stop, screenshot, record `browser_mismatch` evidence and return to the UI. Submit only after the user's final OK in the product UI, then save the confirmation ID and page HTML/screenshot metadata as `agency_receipt` evidence. Never put `.env` secrets (or an unmasked EIN in logs) into the sandbox page.
