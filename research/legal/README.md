# research/legal

A catalog of tax credits a New York small business might qualify for: NYS, NYC and federal. For each program it
records its official links, what the official page says, how many businesses claim it, and who it's really for (its
niche). Most credits only fit one kind of business or one hiring situation, and those are the ones small businesses
miss: in tax year 2023, only 28 businesses statewide claimed the Hire-a-Veteran credit, and 21 claimed the
Recovery Hiring credit.

```sh
make legal-research                       # writes research/legal/data/catalog.json (~1 min, no keys needed)
make legal-show NICHE=hiring_veterans     # credits by niche, fewest claimants first
make legal-show ID=nys_hire_a_veteran     # one program in full
make legal-match DOMAIN=warbyparker.com   # credits a research/company profile may qualify for, with form PDFs
make legal-seeds                          # crawl every program page and form into the kb
make legal-load-kb                        # programs -> kb incentive rows, forms -> kb form rows (needs SurrealDB)
make legal-test                           # no network
```

`uv run legal-research --help` lists more: `niches`, `links [--authority form]`, `run --search`, `run --only <ids>`.

## How it works

| Step | Source | Gives |
|---|---|---|
| Discover | index pages in [catalog/sources.toml](catalog/sources.toml): DTF Article 9-A and 22 credit lists, NYC DOF business benefits, NYC SBS incentives | one program per linked page; id from the URL (`nys_hire_a_veteran`) |
| Curate | [catalog/programs.toml](catalog/programs.toml) | federal credits (FICA tip, R&D, WOTC, ...), NYC programs not on an index, corrections |
| Read | each program's official page (`<main>` only) | eligibility, amount, forms (PDF and instructions), related official links, "Updated" date, refundable, pre-approval and status hints |
| Count | data.ny.gov [4skq-w2i6](https://data.ny.gov/d/4skq-w2i6) | claimants, dollars and average per NYS credit, newest tax year, certifying agency |
| Tag | [catalog/niches.toml](catalog/niches.toml) | 33 niches (restaurants, breweries, film, farms, hiring veterans, ...) with NAICS prefixes and keywords for matching a company profile |
| Search (`--search`) | Tavily, then Nimble, limited to official domains | leads in `candidates`, for a person to review; never fetched |

`status` is `active` only when it's curated, or when the page is live, the credit had claimants in the last three
years and the page has no expiry wording. Otherwise it's `unknown`, and `status_basis` says why. Claimed credits
with no program page are listed under `unmatched_claims`.

## Safety

Only government hosts are fetched (`*.ny.gov`, `*.nyc.gov`, `irs.gov` and a few others in `config.py`), over https,
following robots.txt and waiting 0.5 s between requests to a host. Redirects are followed only to other official
hosts. Hosts that return 403 to direct requests (nysenate.gov, amlegal) go through Firecrawl when
`FIRECRAWL_API_KEY` is set. Page text is stored as data in short single-line strings. `data/` is git-ignored.

## Next

- Profile matching (`match.py`, `legal-research match <domain>`) is keyword and NAICS-prefix based; it doesn't read
  eligibility rules (employee counts, location, pre-approval) yet, so treat matches as leads.
- Load niche rules as kb `criterion` rows once `kb.add_criterion` can upsert (it creates a new row on every call today).
- More claim data: data.ny.gov `6axi-iwd2` (Article 9-A by credit since 2001) and `84qh-f5nv` (by industry).
- Status needs a person or an LLM to read `hints.status`: e.g. Commercial Security credit applications to DCJS are due
  Oct 31, and the federal WOTC lapsed for hires after 2025-12-31.
