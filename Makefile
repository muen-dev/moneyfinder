# moneyfinder commands, run from the repo root. `make` lists them.
#
#   make business-fetch ID=owner-joespizza-com Q='from:gusto.com OR subject:invoice' N=500
#   make kb-search Q='credit for hiring veterans'
#   make company-research DOMAIN=joespizza.com
#
# Arguments are read by the shell ("$$Q"), so values with spaces or quotes pass through intact.

.DEFAULT_GOAL := help
.PHONY: help setup test \
	business-serve business-list business-fetch business-disconnect business-test \
	company-research company-show company-keys company-test \
	legal-research legal-show legal-seeds legal-load-kb legal-test \
	kb-up kb-down kb-init kb-seed kb-crawl kb-ingest kb-search kb-embed kb-missed kb-stats

PORT ?= 8000

help: ## List commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  \033[36m%-21s\033[0m %s\n", $$1, $$2}'

setup: ## Install every package's dependencies and the commit guard hook
	git config core.hooksPath .githooks
	cd research/business && uv sync
	cd research/company && uv sync
	cd research/legal && uv sync
	cd kb && uv sync

test: business-test company-test legal-test ## Run all tests

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

kb-init: ## Apply the database schema (safe to re-run)
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
