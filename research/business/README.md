# research/business

Collects context about a business so we can match it to tax credits and grants.
So far this folder has a **read-only Gmail connector** and a local dev server. The business owner
clicks "Sign in with Google", approves read-only access, and we pull their recent mail (invoices,
payroll, vendors, agency letters) as JSONL for the analysis step.

## One-time Google Cloud setup

1. Go to https://console.cloud.google.com and create a project (or pick an existing one).
2. **Enable the Gmail API:** APIs & Services → Library → "Gmail API" → Enable.
3. **Configure consent:** Google Auth Platform → Get started.
   - App name: `moneyfinder`. Support email: yours.
   - Audience: **External**.
   - Leave publishing status as **Testing**.
4. **Add test users:** Audience → Test users → add the Gmail or Workspace address of each
   business you'll connect. While the app is in Testing, only these accounts can sign in
   (100 max).
5. **Add the scope:** Data Access → Add or remove scopes → `https://www.googleapis.com/auth/gmail.readonly`.
6. **Create the OAuth client:** Clients → Create client → Application type **Web application**.
   - Authorized redirect URIs: `http://localhost:8000/oauth/callback`. Use exactly this,
     including the port. If you run on another port, register that one instead.
   - Download the JSON and save it as `research/business/credentials.json`. Git ignores this file.

## Run the dev server

From the repo root:

```sh
make setup              # dependencies + commit guard hook (once per clone)
make business-serve     # then open http://localhost:8000
```

1. Click **Sign in with Google**. The owner signs in and approves read-only Gmail access.
2. **Company domain:** the owner enters their company's website domain. It's prefilled from their email
   unless that's a free mail provider like gmail.com. Saving it starts public-data research in the background
   (website, BBB, LinkedIn, NY records, news; see `research/company/README.md`). The business page shows
   the status (queued/running/done/failed), refreshes until research finishes, and lists every fact with
   links to its sources. **Re-run research** and **Change domain** are on the same card. Research needs
   `research/company/.env.local` with the scraper API keys.
3. The business page opens. Click **Fetch mail**: by default the last year, minus
   Promotions/Social, up to 200 messages. You can change the Gmail search query and the limit.
4. Browse messages and top sender domains on the page. The data is in `data/<id>/messages.jsonl`.
5. **Disconnect and delete data** revokes Google access and removes the token, fetched mail, company domain
   and research output.

Each business's id comes from its Google address: `owner@joespizza.com` becomes `owner-joespizza-com`.

## Without the browser

```sh
make business-list
make business-fetch ID=owner-joespizza-com Q='from:gusto.com OR subject:invoice' N=500
make business-disconnect ID=owner-joespizza-com   # revokes access, deletes token + mail
```

These wrap `uv run business-research <command>`, which also works from inside this folder.

Each line of `messages.jsonl` has these fields:
`id, thread_id, date, sender, sender_domain, to, subject, snippet, body, labels, attachments`.

## Handling real business data

- **The dashboard has no login of its own.** Anyone who can reach the port can read every
  connected inbox. The server only listens on `127.0.0.1`. Don't tunnel or port-forward it.
- **Tokens and mail stay on this machine.** They live in `.tokens/` and `data/`. Both are
  git-ignored (here and in the root `.gitignore`) and readable only by your user account
  (0600/0700). Fetched mail can only be written there. The commit hook `make setup` installs
  (`.githooks/pre-commit`) rejects these files even if someone runs `git add -f`.
- **Sign-in protections:** the Google sign-in uses `state` and PKCE. Every action button needs
  a CSRF token. Requests with an unknown `Host` header are rejected (this blocks DNS-rebinding
  attacks). Pages are served with a strict CSP and mail content is HTML-escaped.
- **Delete data when you're done:** disconnect a business once its data has been used.
  Disconnecting is also the right answer if an owner asks to be removed.

## Things to know

- **"Google hasn't verified this app"**: expected while the app is in Testing. Click
  Continue.
- **Tokens expire after 7 days in Testing mode.** When that happens, sign in with Google again.
- **`gmail.readonly` is a restricted scope.** Publishing to production needs Google's
  verification plus a third-party security assessment, so stay in Testing for now.
- **Workspace accounts:** the domain admin may block unverified apps. They can allow the
  client ID under Admin console → Security → API controls.
- **`redirect_uri_mismatch`** means the redirect URI on the client doesn't match
  `http://localhost:<port>/oauth/callback` exactly.

## Config overrides

| Env var | Default |
|---|---|
| `GMAIL_CLIENT_SECRETS` | `research/business/credentials.json` |
| `GMAIL_TOKEN_DIR` | `research/business/.tokens/` |
| `BUSINESS_DATA_DIR` | `research/business/data/` |

## Layout

```
src/business_research/
  cli.py            serve / list / fetch / disconnect
  config.py         paths
  ids.py            business ids (filesystem-safe slugs)
  store.py          fetched mail on disk (JSONL)
  company.py        company domain (data/<id>/business.json) + background research (data/<id>/company/)
  gmail/auth.py     OAuth web flow, per-business token store, refresh, revoke
  gmail/client.py   Gmail API: profile, paginated search, get message
  gmail/parse.py    MIME payload -> EmailMessage (plain text, HTML fallback, attachments)
  web/              Flask dev server, templates, static assets
tests/              parser, ids, web security, and the company-domain flow (research mocked, no network)
```
