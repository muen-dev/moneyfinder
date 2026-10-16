# research/company

Turns a company domain into a **CompanyProfile**: the public facts that matter for matching a New York
small business to tax credits and grants. Every fact carries its sources (`url`, `via`, `fetched_at`) and a
confidence. When sources disagree, all the values are kept side by side.

## Setup

```sh
make setup                         # from the repo root (or: cd research/company && uv sync)
cp research/company/.env.example research/company/.env.local   # then fill in the keys
make company-keys                  # shows which keys are set; never prints values
```

| Env var | Used for |
|---|---|
| `FIRECRAWL_API_KEY` | company website (map + scrape with JSON extraction), BBB profile page |
| `TAVILY_API_KEY` | search: BBB and LinkedIn discovery, news and signals |
| `NIMBLE_API_KEY` | fallback search and BBB page extraction when Tavily or Firecrawl fail |
| AWS credentials, `AWS_REGION`, `BEDROCK_MODEL_ID` | optional LLM summary (skipped when no AWS credentials) |
| `COMPANY_DATA_DIR` | output folder (default `research/company/data/`) |

`.env.local` and `data/` are git-ignored. Output files are owner-only (0600, folders 0700).

## Run

```sh
make company-research DOMAIN=warbyparker.com      # writes data/warbyparker.com/profile.json + raw/
make company-show DOMAIN=warbyparker.com [JSON=1]
make company-test                                 # no network
```

`uv run company-research run <domain> [--only website,bbb] [--no-llm] [--out DIR]` does the same from this folder.

## Sources

| Collector | How | Gives |
|---|---|---|
| `website` | Firecrawl map, then scrape the homepage plus about, contact, careers and locations pages (JSON extraction) | name, legal name, description, products, industry, HQ address, locations, founded, roles, social links, job-board links |
| `bbb` | Tavily search restricted to bbb.org, then Firecrawl (Nimble fallback) on the profile page | rating, accreditation, years in business, started, entity type, address |
| `linkedin` | Tavily search restricted to linkedin.com; **snippet only** | page URL, followers, industry, HQ, employee count |
| `nys_dos` | data.ny.gov "Active Corporations" (Socrata), exact name match | legal name, entity type, state of formation, county, DOS id, filing date |
| `nyc_open_data` | NYC SBS certified businesses (matched by website) and DCWP licenses (by name) | M/WBE certification, NAICS, licenses, borough |
| `news` | two Tavily searches (news and general) | hiring, expansion/investment, R&D, awards, certification mentions |
| `llm` (optional) | Bedrock Converse over the merged facts | summary, NAICS guess, incentive signals (low confidence, labeled as LLM) |

The website runs first. Its company name, address and LinkedIn link steer the other collectors, which then
run concurrently. Each one has timeouts and fails on its own. The profile lists each collector's status.

## Output (`profile.json`)

```jsonc
{
  "schema_version": 1, "domain": "warbyparker.com", "generated_at": "...",
  "inputs": {"domain": "...", "business_id": "...", "contact_email": "...", "email_domain_matches": true},
  "best": {"legal_name": "WARBY PARKER INC.", "nyc_borough": "Manhattan", "products_services": ["Eyeglasses", ...]},
  "fields": {                      // claims, highest confidence first; for single-valued fields the rest are conflicts
    "legal_name": [{"value": "WARBY PARKER INC.", "confidence": 0.93,
                    "sources": [{"url": "https://data.ny.gov/...", "via": "socrata:data.ny.gov", "fetched_at": "..."}],
                    "collectors": ["nys_dos", "bbb"]}]
  },
  "collectors": {"website": {"status": "ok", "error": null, "duration_s": 11.5, "facts": 17}, ...}
}
```

Fields are listed in `src/company_research/profile.py` (`FIELDS`). `raw/` keeps every API request and response
for audit. API keys are never recorded.

## Safety and terms

- **Domains** are normalized to the registrable domain (no scheme, path, `www.` or subdomain). IPs, ports,
  credentials, `localhost`, `.local`, `.internal` and names without a public suffix are rejected.
- **We never fetch user-supplied or scraped URLs from this machine.** Pages go through Firecrawl or Nimble.
  Direct HTTP is only used for fixed hosts: the three provider APIs plus data.ny.gov and
  data.cityofnewyork.us. Scraped links are never followed. The site map is limited to the company's own host,
  and only bbb.org profile URLs matching a strict pattern are read.
- **Scraped text is untrusted.** It is stored and shown as data (escaped in the web UI, and only http(s)
  links are rendered). The LLM step gets it inside delimiters, capped in length, and its reply is accepted only
  as a few short text fields with URLs stripped.
- **LinkedIn:** public search-result snippets only. We never request linkedin.com and never log in, use
  cookies, or get around auth walls or rate limits. **BBB:** bbb.org's robots.txt allows `/us/*/*/profile/*`
  without query strings, which is all we read. **Company sites:** the owner enters their own domain at signup.

## In the signup flow

`research/business` depends on this package (uv path source). After Google sign-in, the owner is asked for their
company domain, prefilled from their email unless it's a free mail provider. Saving it starts
`company_research.pipeline.research(...)` in a background thread. The output goes to
`research/business/data/<id>/company/`, so "Disconnect and delete data" removes it.

## Next steps

- The Bedrock step is written but hasn't run live (no AWS credentials here). Converse can't reach Claude models
  newer than Opus 4.6. For those, switch to the `anthropic` SDK's Bedrock Mantle client.
- More sources: NYS Empire State Development M/WBE directory, SAM.gov, the full NYS DOS filing history, and
  NYC DOHMH or SLA licenses for food and alcohol businesses.
- Write the profile into the kb's `business` table so `kb missed` can use it.
