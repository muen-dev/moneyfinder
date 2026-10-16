# moneyfinder
money finder for NYC residents.

- event-context: pre-event stuff
- kb: data lake + knowledge base of NY tax incentives that agents search and cite (see kb/README.md)
- form-filling: use agent browser to fill out the forms
- research/business: getting business context (Gmail connector + company-domain signup)
- research/company: public-data company profile from a domain: website, BBB, LinkedIn, NY records, news (see research/company/README.md)
- research/legal: finding applicable tax credits

## Commands

Run everything from the repo root with `make`. Run `make` by itself to list every command.

```sh
make setup            # install all packages + the commit guard hook (once per clone)
make business-serve   # Gmail connector dev server: http://localhost:8000
make company-research DOMAIN=joespizza.com   # public-data company profile
make kb-up kb-init    # local SurrealDB + schema for the knowledge base
make test
```

Real business data (fetched mail, OAuth tokens, `credentials.json`, `.env` files) is git-ignored.
`.githooks/pre-commit` blocks it from commits even if it's force-added.

---
- AWS Bedrock for LLM tokens
- SurrealDB for Agent Context
- AI Web scrapers (Tavily, Firecrawl, Nimble) to pull BBB and other relevant public business info
- email connector to get businesses' functions and internals of how they work
- *If time permits*: Then get Plaid as a bank link connector to see when the money comes back in (Nick has a Sandbox-enabled Demo account)