"""Local dev server: connect a business's Gmail with Google sign-in, then fetch and browse its mail.

Serves 127.0.0.1 only. The dashboard has no login of its own, so anyone who can reach the port
can read every connected inbox. Don't expose it beyond your machine.
"""

import secrets
from urllib.parse import urlsplit

from company_research.domain import InvalidDomain
from company_research.profile import FIELDS
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from googleapiclient.errors import HttpError

from .. import company, config, inbox, store
from ..gmail import auth
from ..gmail.client import DEFAULT_QUERY, GmailClient

MAX_LIMIT = 2000

# Profile fields shown up front on the business page, in order. The evidence table below has every field.
GLANCE = (
    "legal_name", "dba", "industry", "naics", "hq_address", "nyc_borough", "county", "entity_type",
    "state_of_formation", "founded_year", "years_in_business", "employee_count", "ny_dos_id",
    "ny_dos_filing_date", "phone", "linkedin_url", "linkedin_followers", "bbb_rating", "bbb_accredited",
)
SIGNALS = (
    "incentive_signals", "ownership_certifications", "nyc_licenses", "hiring_signals", "expansion_signals",
    "rd_tech_signals", "awards", "news",
)
COLLECTOR_NAMES = {
    "website": "Company website",
    "bbb": "Better Business Bureau",
    "linkedin": "LinkedIn",
    "nys_dos": "NY Department of State",
    "nyc_open_data": "NYC Open Data",
    "news": "News and web",
    "llm": "AI summary",
}

# Mail content is untrusted HTML-adjacent text; nothing on these pages needs inline or third-party code.
CSP = (
    "default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self'; "
    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
)


def create_app(port: int) -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)  # sessions only need to outlive the OAuth round trip
    # Lax, not Strict: the session must survive Google's cross-site redirect back to the callback.
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

    canonical_host = f"localhost:{port}"
    allowed_hosts = {canonical_host, f"127.0.0.1:{port}"}
    redirect_uri = f"http://{canonical_host}/oauth/callback"

    @app.before_request
    def guard():
        # An unknown Host means a DNS-rebinding page is trying to read this server.
        if request.host not in allowed_hosts:
            abort(400)
        # Cookies are per-host and Google redirects to localhost, so keep the browser there.
        if request.host != canonical_host and request.method == "GET":
            return redirect(f"http://{canonical_host}{request.full_path}")
        if request.method == "POST":
            token = session.get("csrf")
            if not token or not secrets.compare_digest(token, request.form.get("csrf", "")):
                abort(403)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = CSP
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    # Scraped URLs are attacker-controlled: only http(s) ever becomes a link.
    app.jinja_env.filters["http_url"] = _http_url
    app.jinja_env.filters["host"] = _host
    app.jinja_env.filters["short_url"] = _short_url
    app.jinja_env.filters["confidence"] = _confidence

    @app.context_processor
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return {"csrf": session["csrf"]}

    @app.get("/")
    def index():
        businesses = [
            {
                "conn": conn,
                "count": len(store.read_messages(conn.business_id)),
                "fetched_at": store.fetched_at(conn.business_id),
                "domain": company.get_domain(conn.business_id),
                "research": company.status(conn.business_id),
            }
            for conn in auth.list_connections()
        ]
        return render_template(
            "index.html",
            businesses=businesses,
            setup_missing=not config.CLIENT_SECRETS_FILE.exists(),
            client_secrets=config.CLIENT_SECRETS_FILE,
            redirect_uri=redirect_uri,
        )

    @app.get("/login")
    def login():
        try:
            pending = auth.start_login(redirect_uri)
        except FileNotFoundError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))
        session["oauth"] = {"state": pending.state, "code_verifier": pending.code_verifier}
        return redirect(pending.auth_url)

    @app.get("/oauth/callback")
    def oauth_callback():
        pending = session.pop("oauth", None)
        if error := request.args.get("error"):
            flash(f"Google sign-in didn't complete ({error}).", "error")
            return redirect(url_for("index"))
        if not pending or not secrets.compare_digest(pending["state"], request.args.get("state", "")):
            flash("That sign-in link expired or didn't start here. Try again.", "error")
            return redirect(url_for("index"))
        try:
            conn = auth.finish_login(redirect_uri, request.args.get("code", ""), pending["code_verifier"])
        except auth.LoginError as e:
            flash(str(e), "error")
            return redirect(url_for("index"))
        if not company.get_domain(conn.business_id):
            flash(f"Connected {conn.email}. One more step: your company's website.", "ok")
            return redirect(url_for("domain_form", business_id=conn.business_id))
        flash(f"Connected {conn.email}. Fetch mail below.", "ok")
        return redirect(url_for("business", business_id=conn.business_id))

    @app.get("/businesses/<business_id>")
    def business(business_id: str):
        conn = _connection_or_404(business_id)
        messages = store.read_messages(business_id)
        research = company.status(business_id)
        return render_template(
            "business.html",
            conn=conn,
            messages=messages,
            mail=inbox.summarize(messages),
            fetched_at=store.fetched_at(business_id),
            default_query=DEFAULT_QUERY,
            max_limit=MAX_LIMIT,
            domain=company.get_domain(business_id),
            research=research,
            profile=company.profile(business_id),
            fields=FIELDS,
            glance=GLANCE,
            signals=SIGNALS,
            collector_names=COLLECTOR_NAMES,
            refresh=bool(research and research.get("status") in ("queued", "running")),
        )

    @app.get("/businesses/<business_id>/domain")
    def domain_form(business_id: str):
        conn = _connection_or_404(business_id)
        current = company.get_domain(business_id)
        return render_template(
            "domain.html", conn=conn, value=current or company.suggested_domain(conn.email), current=current
        )

    @app.post("/businesses/<business_id>/domain")
    def save_domain(business_id: str):
        conn = _connection_or_404(business_id)
        raw = request.form.get("domain", "")
        try:
            domain = company.set_domain(business_id, raw)
        except InvalidDomain as e:
            current = company.get_domain(business_id)
            return render_template("domain.html", conn=conn, value=raw[:300], current=current, error=str(e)), 400
        _start_research(business_id, domain, conn.email)
        return redirect(url_for("business", business_id=business_id))

    @app.post("/businesses/<business_id>/research")
    def rerun_research(business_id: str):
        conn = _connection_or_404(business_id)
        domain = company.get_domain(business_id)
        if not domain:
            return redirect(url_for("domain_form", business_id=business_id))
        _start_research(business_id, domain, conn.email)
        return redirect(url_for("business", business_id=business_id))

    @app.post("/businesses/<business_id>/fetch")
    def fetch(business_id: str):
        _connection_or_404(business_id)
        query = request.form.get("query", "").strip() or DEFAULT_QUERY
        try:
            limit = min(max(int(request.form.get("limit", "200")), 1), MAX_LIMIT)
        except ValueError:
            abort(400)
        try:
            conn = auth.load(business_id)
            messages = GmailClient(conn.credentials).search(query, limit)
            count = store.write_messages(store.messages_path(business_id), messages)
        except auth.NotConnectedError as e:
            flash(str(e), "error")
        except HttpError as e:
            flash(f"Gmail API error: {e.reason}", "error")
        else:
            flash(f"Fetched {count} messages.", "ok")
        return redirect(url_for("business", business_id=business_id))

    @app.post("/businesses/<business_id>/disconnect")
    def disconnect(business_id: str):
        conn = _connection_or_404(business_id)
        revoked = auth.disconnect(business_id)
        store.delete_messages(business_id)  # removes data/<id>/: mail, company domain and research
        status = "Access revoked" if revoked else "Token deleted, but Google didn't confirm the revoke"
        flash(f"{status} for {conn.email}; fetched mail, company domain and research deleted.", "ok")
        return redirect(url_for("index"))

    return app


def _start_research(business_id: str, domain: str, email: str) -> None:
    if company.start(business_id, domain, email):
        flash(f"Researching {domain} in the background. This page refreshes until it's done.", "ok")
    else:
        flash("Research is already running for this business.", "error")


def _http_url(url) -> str | None:
    if not isinstance(url, str):
        return None
    parts = urlsplit(url)
    return url if parts.scheme in ("http", "https") and parts.netloc else None


def _host(url) -> str:
    """'https://www.bbb.org/us/...' -> 'bbb.org'; empty for anything that isn't an http(s) URL."""
    if not _http_url(url):
        return ""
    host = urlsplit(url).hostname or ""
    return host.removeprefix("www.")


def _short_url(url) -> str:
    """'https://www.linkedin.com/company/acme/' -> 'linkedin.com/company/acme'."""
    if not _http_url(url):
        return str(url)
    parts = urlsplit(url)
    return _host(url) + parts.path.rstrip("/")


def _confidence(value) -> str:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "low"
    return "high" if value >= 0.75 else "medium" if value >= 0.5 else "low"


def _connection_or_404(business_id: str) -> auth.Connection:
    try:
        return auth.get(business_id)
    except (ValueError, auth.NotConnectedError):
        abort(404)
