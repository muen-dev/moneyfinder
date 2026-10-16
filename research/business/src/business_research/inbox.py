"""What a business's fetched mail says about it: which agencies, payroll, banks and vendors write to it."""

from collections import Counter

# Category -> (what it suggests for incentive matching, sender domains). A sender matches a listed
# domain or any subdomain of it. Government is any .gov sender.
CATEGORIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "Government": ("Tax and licensing agencies already have a file on this business", ()),
    "Payroll and HR": (
        "Runs payroll, so hiring and wage credits may apply",
        ("gusto.com", "adp.com", "paychex.com", "rippling.com", "justworks.com", "trinet.com", "deel.com",
         "bamboohr.com", "paylocity.com", "zenefits.com"),
    ),
    "Hiring": (
        "Recruiting, so new-hire credits may apply",
        ("indeed.com", "greenhouse.io", "lever.co", "ziprecruiter.com", "workable.com", "wellfound.com", "glassdoor.com"),
    ),
    "Accounting and tax": (
        "Books and filings, where unclaimed credits show up",
        ("intuit.com", "quickbooks.com", "xero.com", "bill.com", "freshbooks.com", "avalara.com", "taxjar.com",
         "bench.co", "pilot.com", "expensify.com"),
    ),
    "Banking and lending": (
        "Financing and capital investment",
        ("chase.com", "bankofamerica.com", "wellsfargo.com", "citi.com", "citibank.com", "capitalone.com",
         "americanexpress.com", "mercury.com", "brex.com", "ramp.com", "svb.com", "td.com", "ondeck.com", "bluevine.com"),
    ),
    "Payments and sales": (
        "Revenue channels",
        ("stripe.com", "squareup.com", "square.com", "shopify.com", "paypal.com", "toasttab.com", "clover.com"),
    ),
    "Insurance": (
        "Workers' comp and health plans",
        ("thehartford.com", "nextinsurance.com", "hiscox.com", "statefarm.com", "progressive.com", "libertymutual.com",
         "travelers.com", "embroker.com", "vouch.us", "oscarhealth.com", "uhc.com", "aetna.com", "emblemhealth.com"),
    ),
    "Property and utilities": (
        "Space and energy use, for property and energy programs",
        ("coned.com", "nationalgridus.com", "nationalgrid.com", "pseg.com", "nyseg.com", "wework.com", "industriousoffice.com"),
    ),
    "Contracts and legal": (
        "Leases, agreements and entity filings",
        ("docusign.net", "docusign.com", "dropboxsign.com", "hellosign.com", "pandadoc.com", "legalzoom.com", "carta.com",
         "clerky.com", "northwestregisteredagent.com"),
    ),
}


def category(domain: str) -> str | None:
    domain = domain.lower()
    if domain.endswith(".gov"):
        return "Government"
    for name, (_, domains) in CATEGORIES.items():
        if any(domain == d or domain.endswith(f".{d}") for d in domains):
            return name
    return None


def summarize(messages: list[dict]) -> dict:
    """Counts, date range, busiest senders, and known senders grouped by category (largest first)."""
    senders = Counter(m.get("sender_domain") or "" for m in messages)
    groups: dict[str, list[tuple[str, int]]] = {}
    for domain, n in senders.most_common():
        if name := category(domain):
            groups.setdefault(name, []).append((domain, n))
    dates = sorted(m["date"][:10] for m in messages if m.get("date"))
    return {
        "messages": len(messages),
        "senders": len(senders),
        "attachments": sum(len(m.get("attachments") or []) for m in messages),
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
        "top_senders": senders.most_common(15),
        "categories": [
            {"name": name, "hint": CATEGORIES[name][0], "senders": found, "count": sum(n for _, n in found)}
            for name, found in sorted(groups.items(), key=lambda item: -sum(n for _, n in item[1]))
        ],
    }
