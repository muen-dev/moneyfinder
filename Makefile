# moneyfinder commands, run from the repo root. `make` lists them.
#
#   make business-fetch ID=owner-joespizza-com Q='from:gusto.com OR subject:invoice' N=500
#   make kb-search Q='credit for hiring veterans'
#   make company-research DOMAIN=joespizza.com
#   make legal-match DOMAIN=warbyparker.com
#   make demo                      # then open http://localhost:8000
#   make dossier DOMAIN=themaincapital.com && make dossier-push ID=themaincapital.com
#   make dossier-get SLUG=themaincapital-com
#
# Arguments are read by the shell ("$$Q"), so values with spaces or quotes pass through intact.

.DEFAULT_GOAL := help
.PHONY: help setup test demo pipeline-test evals \
	business-serve business-list business-fetch business-disconnect business-test \
	company-research company-show company-keys company-test \
	legal-research legal-show legal-match legal-seeds legal-load-kb legal-test \
	kb-up kb-down kb-init kb-seed kb-crawl kb-ingest kb-search kb-embed kb-missed kb-stats kb-ping kb-test \
	dossier dossier-push dossier-get

PORT ?= 8000

help: ## List commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  \033[36m%-21s\033[0m %s\n", $$1, $$2}'

setup: ## Install every package's dependencies and the commit guard hook
	git config core.hooksPath .githooks
	cd research/business && uv sync
	cd research/company && uv sync
	cd research/legal && uv sync
	cd kb && uv sync

test: business-test company-test legal-test kb-test pipeline-test ## Run all tests

# MVP demo

demo: business-serve ## The web app: company profiles, matched credits, unclaimed-funds demo at /unclaimed/ [PORT=8000]

pipeline-test: ## Unclaimed-funds pipeline checks (src/, synthetic data)
	python3 tests/test_pipeline.py

evals: ## Unclaimed-funds evals on synthetic profiles
	python3 evals/run_evals.py

# Dossiers: one form-ready JSON per business (research/), loaded into SurrealDB for the form filler

dossier: ## Build dossier.json: DOMAIN=<domain> and/or BUSINESS=<business id> [NO_LLM=1]
	@test -n "$$DOMAIN$$BUSINESS" || { echo "usage: make dossier DOMAIN=themaincapital.com [BUSINESS=<id>] [NO_LLM=1]"; exit 1; }
	cd research/business && uv run business-research dossier $${DOMAIN:+"$$DOMAIN"} $${BUSINESS:+--business-id "$$BUSINESS"} $${NO_LLM:+--no-llm}

dossier-push: ## Load dossier.json into SurrealDB: ID=<slug|domain|path to dossier.json> or ALL=1 [YEAR=2025]
	@test -n "$$ID$$ALL" || { echo "usage: make dossier-push ID=themaincapital.com   (or ALL=1 for every research/*/data/**/dossier.json)"; exit 1; }
	uv run --project kb kb dossier-push $${ALL:+--all} $${ID:+"$$ID"} $${YEAR:+--tax-year "$$YEAR"}

dossier-get: ## Print fn::business_dossier from SurrealDB: SLUG=<slug, e.g. themaincapital-com>
	@test -n "$$SLUG" || { echo "usage: make dossier-get SLUG=themaincapital-com"; exit 1; }
	cd kb && uv run kb dossier-get "$$SLUG"

# research/business: Gmail connector

business-serve: ## Dev server with Google sign-in [PORT=8000]
	cd research/business && uv run business-research serve --port $(PORT)

business-list: ## Connected businesses and their ids
	cd research/business && uv run business-research list

business-fetch: ## Fetch mail to research/business/data/: ID=<id> [Q='gmail query'] [N=200]
	@test -n "$$ID" || { echo "usage: make business-fetch ID=<id> [Q='gmail query'] [N=200]   (ids: make business-list)"; exit 1; }
	cd research/business && uv run business-research fetch "$$ID" $${Q:+-q "$$Q"} $${N:+-n "$$N"}

business-disconnect: ## Revoke Gmail access, delete token and fetched mail: ID=<id>
	@test -n "$$ID" || { echo "usage: make business-disconnect ID=<id>   (ids: make business-list)"; exit 1; }
	cd research/business && uv run business-research disconnect "$$ID"

business-test: ## research/business tests
	cd research/business && uv run pytest -q

# research/company: public-data company profiles (website, BBB, LinkedIn, NY records, news)

company-research: ## Research a company, write research/company/data/<domain>/: DOMAIN=<domain> [EMAIL=...] [ONLY=website,bbb]
	@test -n "$$DOMAIN" || { echo "usage: make company-research DOMAIN=joespizza.com [EMAIL=owner@joespizza.com] [ONLY=website,bbb]"; exit 1; }
	cd research/company && uv run company-research run "$$DOMAIN" $${EMAIL:+--email "$$EMAIL"} $${ONLY:+--only "$$ONLY"}

company-show: ## Print a stored company profile: DOMAIN=<domain> [JSON=1]
	@test -n "$$DOMAIN" || { echo "usage: make company-show DOMAIN=joespizza.com [JSON=1]"; exit 1; }
	cd research/company && uv run company-research show "$$DOMAIN" $${JSON:+--json}

company-keys: ## Which scraper API keys are configured (never prints values)
	cd research/company && uv run company-research keys

company-test: ## research/company tests
	cd research/company && uv run pytest -q

# research/legal: tax-credit program catalog (official links, page data, claim counts, niches)

legal-research: ## Build research/legal/data/catalog.json [SEARCH=1 to also search for niche programs]
	cd research/legal && uv run legal-research run $${SEARCH:+--search}

legal-show: ## Print credits by niche, fewest claimants first [NICHE=<id>] [ID=<program id>]
	cd research/legal && uv run legal-research show $${ID:+"$$ID"} $${NICHE:+--niche "$$NICHE"}

legal-match: ## Credits a stored company profile may qualify for: DOMAIN=<domain> [JSON=1]
	@test -n "$$DOMAIN" || { echo "usage: make legal-match DOMAIN=warbyparker.com [JSON=1]   (profiles: research/company/data/)"; exit 1; }
	cd research/legal && uv run legal-research match "$$DOMAIN" $${JSON:+--json}

legal-seeds: ## Export catalog links as kb seeds and crawl them into the kb
	cd research/legal && uv run legal-research seeds
	cd kb && uv run kb seed --file ../research/legal/data/kb-seeds.toml

legal-load-kb: ## Write programs and forms into the kb's incentive and form tables [YEAR=2025]
	cd research/legal && uv run legal-research load-kb $${YEAR:+--tax-year "$$YEAR"}

legal-test: ## research/legal tests
	cd research/legal && uv run pytest -q

# kb: tax-incentive data lake + knowledge base

kb-up: ## Start local SurrealDB in Docker (port 8000)
	cd kb && docker compose up -d

kb-down: ## Stop local SurrealDB
	cd kb && docker compose down

kb-init: ## Apply the database schema to SurrealDB (safe to re-run)
	cd kb && uv run kb init

kb-seed: ## Crawl seeds/sources.toml [PAGES=200 per seed]
	cd kb && uv run kb seed $${PAGES:+--max-pages "$$PAGES"}

kb-crawl: ## Fetch links discovered during crawls [LIMIT=100]
	cd kb && uv run kb crawl-pending $${LIMIT:+--limit "$$LIMIT"}

kb-ingest: ## Index one URL: URL=<url> [AUTHORITY=form]
	@test -n "$$URL" || { echo "usage: make kb-ingest URL=<url> [AUTHORITY=form]"; exit 1; }
	cd kb && uv run kb ingest "$$URL" $${AUTHORITY:+--authority "$$AUTHORITY"}

kb-search: ## Search the corpus: Q='question'
	@test -n "$$Q" || { echo "usage: make kb-search Q='question'"; exit 1; }
	cd kb && uv run kb search "$$Q"

kb-embed: ## Backfill missing embeddings
	cd kb && uv run kb embed-missing

kb-missed: ## Likely incentives not yet claimed: BUSINESS=<slug> YEAR=<tax year>
	@test -n "$$BUSINESS" -a -n "$$YEAR" || { echo "usage: make kb-missed BUSINESS=<slug> YEAR=<tax year>"; exit 1; }
	cd kb && uv run kb missed "$$BUSINESS" "$$YEAR"

kb-stats: ## Row counts
	cd kb && uv run kb stats

kb-ping: ## Check the SurrealDB connection (root .env: SurrealDB Cloud; kb/.env overrides)
	cd kb && uv run kb ping

kb-test: ## kb tests (in-process SurrealDB, no server needed)
	cd kb && uv run pytest -q
