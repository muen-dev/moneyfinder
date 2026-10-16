"""NYC Open Data: SBS M/WBE certifications (matched by website) and DCWP business licenses (by name)."""

from ..enrich import name_similarity, name_variants, soql_prefix
from ..profile import CollectorResult, clean_text
from ..providers import now
from . import Context, fact

NAME = "nyc_open_data"
HOST = "data.cityofnewyork.us"
SBS_CERTIFIED = "ci93-uc8s"  # SBS Certified Business List (M/WBE, EBE, LBE)
DCWP_LICENSES = "w7w3-xahh"  # DCWP Legally Operating Businesses
VIA = f"socrata:{HOST}"

SBS_COLUMNS = "account_number,vendor_formal_name,vendor_dba,certification,cert_renewal_date,business_description,address1,city,state,zip,website,id6_digit_naics_code,naics_title"
DCWP_COLUMNS = "license_nbr,business_name,dba_trade_name,business_category,license_type,license_status,lic_expir_dd,address_building,address_street_name,address_city,address_state,address_zip,address_borough"


def collect(ctx: Context) -> CollectorResult:
    result = CollectorResult(NAME)
    errors = []
    for part in (_sbs, _dcwp):
        try:
            part(ctx, result)
        except Exception as e:  # each dataset is independent; keep the other's facts
            errors.append(f"{part.__name__.strip('_')}: {e}")
    if errors:
        result.error = "; ".join(errors)
        if not result.facts:
            raise RuntimeError(result.error)
    return result


def _sbs(ctx: Context, result: CollectorResult) -> None:
    """Certified firms list a website, so a domain match is strong evidence."""
    domain = ctx.domain.replace("'", "")
    rows = ctx.providers.socrata(
        HOST, SBS_CERTIFIED, {"$select": SBS_COLUMNS, "$where": f"lower(website) like '%{domain}%'", "$limit": "5"}
    )
    confidence, note = 0.9, "website on the certification matches the domain"
    if not rows:
        variants = [v for name in ctx.names[:2] for v in name_variants(name)][:30]
        if not variants:
            return
        quoted = ", ".join(f"'{v}'" for v in variants)
        rows = ctx.providers.socrata(
            HOST, SBS_CERTIFIED,
            {"$select": SBS_COLUMNS, "$where": f"upper(vendor_formal_name) in ({quoted}) OR upper(vendor_dba) in ({quoted})", "$limit": "5"},
        )
        confidence, note = 0.6, "matched by name only"
    at = now()
    for row in rows[:3]:
        url = f"https://{HOST}/resource/{SBS_CERTIFIED}.json?account_number={row.get('account_number', '')}"

        def add(field_name, value, conf=confidence):
            if value:
                result.facts.append(fact(field_name, value, url, VIA, at, conf, NAME, note))

        cert = clean_text(row.get("certification") or "", 40)
        if cert:
            renew = row.get("cert_renewal_date")
            add("ownership_certifications", f"NYC SBS certified {cert}" + (f" (renews {renew})" if renew else ""))
        add("legal_name", clean_text(row.get("vendor_formal_name") or "", 120), confidence * 0.9)
        if row.get("vendor_dba") and row.get("vendor_dba") != row.get("vendor_formal_name"):
            add("dba", clean_text(row["vendor_dba"], 120), confidence * 0.9)
        if row.get("id6_digit_naics_code"):
            add("naics", {"code": row["id6_digit_naics_code"], "title": row.get("naics_title", "")}, confidence * 0.9)
        add("description", clean_text(row.get("business_description") or "", 600), confidence * 0.7)
        address = ", ".join(filter(None, [row.get("address1"), row.get("city"), row.get("state"), row.get("zip")]))
        add("hq_address", clean_text(address, 200), confidence * 0.8)


def _dcwp(ctx: Context, result: CollectorResult) -> None:
    variants = [v for name in ctx.names[:2] or [ctx.name] for v in name_variants(name)][:30]
    if not variants:
        return
    quoted = ", ".join(f"'{v}'" for v in variants)
    rows = ctx.providers.socrata(
        HOST, DCWP_LICENSES,
        {"$select": DCWP_COLUMNS, "$where": f"upper(business_name) in ({quoted}) OR upper(dba_trade_name) in ({quoted})", "$limit": "25"},
    )
    if not rows and (prefix := soql_prefix(ctx.name)):
        rows = ctx.providers.socrata(
            HOST, DCWP_LICENSES,
            {"$select": DCWP_COLUMNS, "$where": f"upper(dba_trade_name) like '{prefix}%'", "$limit": "25"},
        )
    at = now()
    for row in rows:
        names = [row.get("business_name") or "", row.get("dba_trade_name") or ""]
        similarity = max(name_similarity(a, b) for a in names for b in ctx.names or [ctx.name])
        if similarity < 0.6:
            continue
        confidence = 0.7 if similarity >= 0.99 else 0.4
        note = "matched by name" if similarity >= 0.99 else "similar name only"
        url = f"https://{HOST}/resource/{DCWP_LICENSES}.json?license_nbr={row.get('license_nbr', '')}"
        address = " ".join(filter(None, [row.get("address_building"), row.get("address_street_name")]))
        address = ", ".join(filter(None, [address, row.get("address_city"), row.get("address_state"), row.get("address_zip")]))
        license_info = {
            "title": clean_text(row.get("business_category") or "DCWP license", 80),
            "license": row.get("license_nbr"),
            "status": row.get("license_status"),
            "expires": (row.get("lic_expir_dd") or "")[:10],
            "detail": clean_text(address, 160),
        }
        result.facts.append(fact("nyc_licenses", license_info, url, VIA, at, confidence, NAME, note))
        if address:
            result.facts.append(fact("other_locations", clean_text(address, 160), url, VIA, at, confidence * 0.8, NAME, note))
        if row.get("address_borough"):
            result.facts.append(fact("nyc_borough", row["address_borough"], url, VIA, at, confidence * 0.6, NAME, "location of a licensed premises"))
