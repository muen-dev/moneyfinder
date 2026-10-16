# SurrealDB setup: plug-in guide

Audited 2026-10-16 (read-only: nothing was started, initialized or edited). Run every command from the repo root.

## Status

- **Working:** the `kb` package installs and runs (`uv run kb --help` OK; Python 3.13.13, `surrealdb` SDK 2.0.0). Docker Desktop and Compose v5.4.0 are installed, and ports 8000, 8001 and 8080 are free right now.
- **Missing:** no database exists anywhere. There's no `kb/.env`, no Surreal Cloud endpoint or credentials, no `surreal` CLI, and no AWS credentials, so search is full-text only.
- **Blocking:** the Docker daemon isn't running, so every `kb` command fails with `ConnectionRefusedError: [Errno 61]`. SurrealDB and `make business-serve` both bind `127.0.0.1:8000`.

How kb connects: `kb/src/moneyfinder_kb/config.py` loads **only `kb/.env`**. Defaults: `SURREAL_URL=ws://127.0.0.1:8000`, `SURREAL_USER=root`, `SURREAL_PASS=root`, `SURREAL_NS=moneyfinder`, `SURREAL_DB=kb`. It signs in with a root-level username and password; there's no token support. Variables already exported in your shell override `kb/.env`.

Pick **Option A** (about 5 minutes) unless you specifically want Cloud for the demo.

## Option A: local Docker on port 8001 (fastest)

The Flask app keeps port 8000, because its Google OAuth redirect is registered as `http://localhost:8000/oauth/callback`. SurrealDB moves to host port **8001**; inside the container it still listens on 8000.

```bash
# 1. Start Docker Desktop and wait for the daemon
open -a Docker
until docker info >/dev/null 2>&1; do sleep 2; done

# 2. Edit kb/docker-compose.yml: change the ports line to "127.0.0.1:8001:8000"
#    (leave `--bind 0.0.0.0:8000` in `command:` alone)
sed -i '' 's#"127.0.0.1:8000:8000"#"127.0.0.1:8001:8000"#' kb/docker-compose.yml

# 3. Create kb/.env and point it at 8001 (the example's root/root matches the compose file)
cp kb/.env.example kb/.env
sed -i '' 's#^SURREAL_URL=.*#SURREAL_URL=ws://127.0.0.1:8001#' kb/.env

# 4. Start SurrealDB 3.3.0 and check it answers
make kb-up
curl -s http://127.0.0.1:8001/version      # expect: surrealdb-3.3.0
```

Data lives in the Docker volume `kb_surreal-data`. `make kb-down` keeps it, and `cd kb && docker compose down -v` deletes it. The `kb-up` help text in the Makefile still says "port 8000"; that's cosmetic.

## Option B: Surreal Cloud

Root `.env` has `SURREALDB_ORG_ID` and `SURREALDB_MONEY-FINDER_INSTANCE_ID`, but kb never reads them. They only tell you which instance to open. No endpoint or credentials exist yet.

1. Open https://studio.surrealdb.com, find the instance, and make sure it isn't paused. It must run **SurrealDB 3.x**: the schema uses 3.x syntax and was tested on 3.3.0. If it's on 2.x, upgrade it under Settings > Versions.
2. Under **Connect**, copy the endpoint. Don't type the hostname by hand. With the CLI installed, `surreal cloud instance endpoint <instance-name>` prints the same value.
3. Create namespace `moneyfinder` and database `kb`. If you keep Studio's defaults instead, set `SURREAL_NS` and `SURREAL_DB` to match.
4. Open **Authentication > Root Authentication > + > New system user** and pick the **Owner** role (`kb init` defines tables, functions and analyzers). It has to be a **root-level** user: kb signs in without a namespace or database and can't use tokens.
5. Create `kb/.env` (`cp kb/.env.example kb/.env`) and set:

```dotenv
SURREAL_URL=wss://<endpoint-from-Connect-menu>
SURREAL_USER=<system-user-name>
SURREAL_PASS=<system-user-password>
SURREAL_NS=moneyfinder
SURREAL_DB=kb
```

The trailing `/rpc` is optional, because the SDK strips and re-adds it. `kb/.env` is git-ignored. Then run the Verify steps below. Quick reachability check: `curl -s https://<endpoint>/version`.

## Verify

```bash
make kb-init      # expect: applied 114 schema statements   (safe to re-run)
make kb-stats     # expect: JSON of counters, all 0 on a fresh database
make kb-ingest URL=https://www.tax.ny.gov/pdf/current_forms/ct/ct607i.pdf AUTHORITY=form_instructions
                  # expect: "  new  https://www.tax.ny.gov/pdf/current_forms/ct/ct607i.pdf  <N> chunks"
make kb-search Q='Excelsior jobs tax credit per new job'
                  # expect: "[1] <title>  <url> (p. N)  [form_instructions]" plus a text excerpt
make kb-stats     # expect: sources >= 1, documents >= 1, chunks > 0, embedded 0
```

For more data, run `make kb-seed PAGES=10` and then `make kb-crawl LIMIT=50`. The defaults crawl 200 pages per seed with a 0.5 s delay, which is slow. Failure decoder:

- `ConnectionRefusedError` means the database isn't running or `SURREAL_URL` has the wrong port.
- An auth error usually means the Cloud user isn't root-level.
- A parse error on `kb-init` means the server is older than 3.x.

## Plug research into the kb (`profile.json` to `business`)

`kb missed` reads edges, not profiles, so it needs both a business row **and** assessments.

1. **Input:** `research/company/data/<domain>/profile.json` (from `make company-research`), or `research/business/data/<id>/company/profile.json` (from the signup flow). Use its `best` object and `domain`.
2. **Key:** pick a stable slug for the record id `business:<slug>`, e.g. the domain with non-alphanumerics replaced by `_` (`warbyparker.com` becomes `warbyparker_com`). `kb missed <slug> <year>` takes this same slug.
3. **Write:** call `KB.upsert_business(slug, **fields)` (UPSERT MERGE; `None` values are dropped). The `business` table is SCHEMAFULL, so values must match these types or the write fails:

| `business` field | Type in schema.surql | From `profile.json` |
|---|---|---|
| `name` (required) | `string` | `best.legal_name`, else `best.dba`, else `domain` |
| `website` | `option<string>` | `"https://" + domain` |
| `naics` | `array<string>` | `[best.naics.code]`; the profile has an object `{code, title}` |
| `entity_type` | `"c_corp" \| "s_corp" \| "partnership" \| "llc" \| "sole_prop" \| "nonprofit"` | map the NYS DOS text: "...Limited Liability Company" to `llc`, "...Business Corporation" to `c_corp`, "Not-for-Profit..." to `nonprofit`, "...Partnership" to `partnership`; otherwise omit |
| `county` | `option<string>` | `best.county` |
| `nyc_borough` | `"Manhattan" \| "Brooklyn" \| "Queens" \| "Bronx" \| "Staten Island"` | `best.nyc_borough` only if it is exactly one of these |
| `employees` | `option<int>` | parse the integer out of `best.employee_count` (e.g. "3 employees on LinkedIn"); omit if unclear |
| `annual_revenue` | `option<decimal>` | not in the profile; omit |
| `profile` | `object FLEXIBLE` | the whole `best` dict plus `domain`, `generated_at`, `collectors` |
| `sources` | `array<record<source>>` | leave empty (each entry must be a `source` record) |

4. **Make incentives exist:** `KB.upsert_incentive(slug, name=..., kind=..., jurisdiction=...)`. `fn::missed_opportunities` returns `out.name`.
5. **Assess:** for each candidate incentive, call `KB.assess(business_slug, incentive_slug, tax_year, "likely" | "possible", confidence=..., reasons=[...], evidence=[chunk ids from kb.search()])`. This writes the `eligible_for` edge, unique per business, incentive and year.
6. **Read:** `make kb-missed BUSINESS=warbyparker_com YEAR=2025`. It returns `[]` until step 5 has written edges, and anything with a non-denied `claimed` edge for that year is excluded.

Where to run it: `research/company` doesn't depend on `moneyfinder-kb`. Either run the loader inside kb's environment (`cd kb && uv run python <script> <profile.json>`), or add `moneyfinder-kb = { path = "../../kb", editable = true }` under `[tool.uv.sources]` in `research/company/pyproject.toml`, the same way `research/business` pulls in `company-research`. Keep it **editable**: kb finds `kb/.env` relative to its own source folder. A natural hook is right after `store.write_run(...)` in the company pipeline, or a new `kb load-profile <path>` subcommand.

## Gotchas

- **Port 8000:** `make business-serve` (Flask, `127.0.0.1:8000`, OAuth redirect pinned to 8000) and the stock `kb/docker-compose.yml` (`127.0.0.1:8000`) collide. Whichever starts second fails. Use 8001 for SurrealDB as in Option A.
- **Hyphenated name in root `.env`:** `SURREALDB_MONEY-FINDER_INSTANCE_ID` breaks nothing today, because no code or Make target loads the root `.env`. But `source .env` / `set -a; . ./.env` prints `command not found` **and echoes the whole line, value included**, and the name can't be used as `$VAR`. Rename it to `SURREALDB_MONEYFINDER_INSTANCE_ID` before you ever source that file. python-dotenv parses it fine.
- **`research/legal/.env.local`** ends with a bare `Surreal` line (no `=`, no value). It's a placeholder, not a credential, and nothing loads that file.
- **Embeddings:** Amazon Bedrock Titan Text Embeddings V2 (`EMBED_MODEL=amazon.titan-embed-text-v2:0`, `EMBED_DIM=1024`). It needs AWS credentials (none on this machine: no `~/.aws`, no `AWS_*` vars) plus Bedrock model access in `AWS_REGION`. Leave `EMBED_MODEL` unset and search stays BM25 full-text, which works. `make kb-embed` then exits 1 with "EMBED_MODEL is not set". **Setting `EMBED_MODEL` without working AWS credentials crashes ingest and search**, because the Bedrock call sits outside the error handling. When creds exist, set it and run `make kb-embed` to backfill. Keep `EMBED_DIM=1024` unless you also change the `chunk_vec` index.
- **No Docker-free shortcut:** the SDK's embedded URLs (`mem://`, `surrealkv://`) bundle SurrealDB engine 2.3.10, but the schema needs 3.x. Use Docker or Cloud.
- **`FIRECRAWL_API_KEY`** in `kb/.env` is optional; without it kb uses a built-in HTML extractor. Keys already exist in `research/company/.env.local`, so copy one over yourself if you want cleaner markdown.
- **Shell overrides:** if `SURREAL_URL` etc. are exported in your shell, they win over `kb/.env`.
