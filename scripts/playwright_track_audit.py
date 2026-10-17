#!/usr/bin/env python3
"""Playwright audit of Send/Track wiring. Exit 0 always; prints JSON issues to stdout."""

from __future__ import annotations

import json
import sys
from urllib.parse import urljoin

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"


def issue(sev: str, where: str, msg: str, **extra):
    row = {"severity": sev, "where": where, "message": msg, **extra}
    print(json.dumps(row), flush=True)
    return row


def main() -> int:
    from playwright.sync_api import sync_playwright

    issues: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        console_errors: list[str] = []
        failed_requests: list[str] = []

        page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on(
            "requestfailed",
            lambda r: failed_requests.append(f"{r.method} {r.url} :: {r.failure}"),
        )

        # --- Home / Send shell ---
        resp = page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=20000)
        if not resp or resp.status >= 400:
            issues.append(issue("critical", "/", f"Home status {resp.status if resp else None}"))
        else:
            body = page.content()
            nav = page.locator("nav.nav").inner_text()
            if "Legacy unclaimed UI" in nav or "Legacy unclaimed UI" in body:
                issues.append(issue("critical", "/", "Nav still shows 'Legacy unclaimed UI' (stale server or missed rename)"))
            if "Track" not in nav:
                issues.append(issue("critical", "/", "Nav missing 'Track' link"))
            track_href = page.locator("nav.nav a", has_text="Track").get_attribute("href")
            if track_href and "/track" not in track_href:
                issues.append(issue("high", "/", f"Track nav href unexpected: {track_href}"))
            if "No OAuth client" in body:
                issues.append(
                    issue(
                        "medium",
                        "/",
                        "OAuth credentials.json missing — Connect Gmail blocked (pre-existing setup)",
                        detail="research/business/credentials.json",
                    )
                )

        # --- /track/ ---
        console_errors.clear()
        failed_requests.clear()
        resp = page.goto(f"{BASE}/track/", wait_until="networkidle", timeout=30000)
        status = resp.status if resp else None
        title = page.title()
        body = page.content()
        if status == 404 or "Not Found" in page.locator("body").inner_text()[:200]:
            issues.append(issue("critical", "/track/", f"Track entry 404/Not Found (status={status}) — Flask not serving domain.html"))
        elif status and status >= 400:
            issues.append(issue("critical", "/track/", f"Track status {status}"))
        else:
            if "MoneyFinder Track" not in title and "MoneyFinder Track" not in body:
                issues.append(issue("high", "/track/", f"Title/body missing 'MoneyFinder Track' (title={title!r})"))
            if "Research my business" not in body:
                issues.append(issue("high", "/track/", "Expected Track CTA 'Research my business' not found — may be serving wrong HTML (index.html vs domain.html)"))
            if "Create business profile" in body and "Research my business" not in body:
                issues.append(issue("high", "/track/", "Serving marketing ui/index.html instead of product ui/domain.html"))
            # blue-ish track tokens
            styles = page.locator("style").first.inner_text() if page.locator("style").count() else ""
            if "#0f7b55" in styles and "#0b2545" not in styles.lower() and "#0B2545" not in styles:
                issues.append(issue("medium", "/track/", "Track CSS still looks green-Send (#0f7b55) without navy Track hero (#0b2545)"))
            if "#0b2545" not in styles.lower() and "#0B2545" not in styles:
                # case fold
                if "#0b2545" not in styles.lower():
                    issues.append(issue("medium", "/track/", "Track navy hero token #0b2545 not found in inline CSS"))

        # API from Track page origin
        api = page.evaluate(
            """async () => {
              const r = await fetch('/api/health');
              const j = await r.json().catch(() => ({}));
              return { status: r.status, body: j };
            }"""
        )
        if api.get("status") != 200:
            issues.append(issue("critical", "/api/health", f"Health failed from Track origin: {api}"))
        elif api.get("body", {}).get("surface") != "track":
            issues.append(issue("high", "/api/health", f"Health missing surface=track: {api.get('body')}"))

        tracker = page.evaluate(
            """async () => {
              const r = await fetch('/api/tracker');
              const j = await r.json().catch(() => ({}));
              return { status: r.status, keys: Object.keys(j || {}) };
            }"""
        )
        if tracker.get("status") != 200:
            issues.append(issue("critical", "/api/tracker", f"Tracker API failed: {tracker}"))

        # console / network after track load
        for err in console_errors:
            if "favicon" in err.lower():
                continue
            issues.append(issue("medium", "/track/ console", err))
        for fr in failed_requests:
            if "favicon" in fr.lower():
                continue
            issues.append(issue("medium", "/track/ network", fr))

        # Interact: click Research if present
        if page.locator("button", has_text="Research my business").count():
            page.locator("button", has_text="Research my business").first.click()
            page.wait_for_timeout(500)
            if page.locator("#view-research").count() and page.locator("#view-research").is_visible():
                pass
            elif "website" not in page.content().lower():
                issues.append(issue("medium", "/track/#research", "Research CTA click did not reveal research view"))

        # --- redirects ---
        resp = page.goto(f"{BASE}/unclaimed/", wait_until="domcontentloaded", timeout=15000)
        final = page.url
        if "/track" not in final:
            issues.append(
                issue(
                    "high",
                    "/unclaimed/",
                    f"Expected redirect to /track/, landed on {final} (status={resp.status if resp else None})",
                )
            )

        # --- landing alternate ---
        resp = page.goto(f"{BASE}/track/landing", wait_until="domcontentloaded", timeout=15000)
        if not resp or resp.status >= 400:
            issues.append(issue("low", "/track/landing", f"Marketing landing status {resp.status if resp else None}"))
        else:
            if "Create business profile" not in page.content():
                issues.append(issue("low", "/track/landing", "Expected marketing CTA missing"))

        # --- mock portal ---
        resp = page.goto(f"{BASE}/mock-portal/", wait_until="domcontentloaded", timeout=15000)
        if not resp or resp.status >= 400:
            issues.append(issue("medium", "/mock-portal/", f"status {resp.status if resp else None}"))

        # --- stale :8000 comparison hint ---
        try:
            stale = page.request.get("http://localhost:8000/", timeout=3000)
            if stale.ok:
                html = stale.text()
                if "Legacy unclaimed UI" in html:
                    issues.append(
                        issue(
                            "critical",
                            "http://localhost:8000/",
                            "Stale Flask process still running — shows 'Legacy unclaimed UI' and /track/ 404. Restart make demo.",
                        )
                    )
                track8000 = page.request.get("http://localhost:8000/track/", timeout=3000)
                if track8000.status == 404:
                    issues.append(
                        issue(
                            "critical",
                            "http://localhost:8000/track/",
                            "404 on port 8000 — browser is hitting old process; new code is on the restarted port",
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            issues.append(issue("low", "http://localhost:8000/", f"Could not probe stale server: {exc}"))

        browser.close()

    summary = {
        "base": BASE,
        "issue_count": len(issues),
        "by_severity": {
            s: sum(1 for i in issues if i["severity"] == s) for s in ("critical", "high", "medium", "low")
        },
    }
    print(json.dumps({"summary": summary}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
