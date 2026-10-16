"""Deterministic derivations: NYC borough from an address, NAICS guess from an industry, name matching."""

import re

# NYC ZIP ranges per borough (USPS). Good enough to place an address; not a geocoder.
_BOROUGH_ZIPS = (
    ("Manhattan", 10001, 10282),
    ("Staten Island", 10301, 10314),
    ("Bronx", 10451, 10475),
    ("Brooklyn", 11201, 11256),
    ("Queens", 11004, 11005),
    ("Queens", 11101, 11120),
    ("Queens", 11351, 11697),
)
_BOROUGH_WORDS = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "bronx": "Bronx",
    "staten island": "Staten Island",
    "queens": "Queens",
    "long island city": "Queens",
    "astoria": "Queens",
    "flushing": "Queens",
    "jamaica": "Queens",
}


def borough_from_address(address: str) -> str | None:
    text = address.lower()
    if not re.search(r"\b(ny|new york)\b", text):
        return None
    for zip_code in re.findall(r"\b(1[01]\d{3})(?:-\d{4})?\b", text):
        z = int(zip_code)
        for borough, low, high in _BOROUGH_ZIPS:
            if low <= z <= high:
                return borough
    for word, borough in _BOROUGH_WORDS.items():
        if re.search(rf"\b{word}\b", text):
            return borough
    if re.search(r"new york,?\s+(ny|new york)\b", text):
        return "Manhattan"  # USPS city "New York, NY" is Manhattan
    return None


# Keyword -> (NAICS code, title). First match wins, so specific entries come first.
_NAICS = (
    (r"full[- ]service restaurant|fine dining", "722511", "Full-Service Restaurants"),
    (r"fast casual|quick[- ]service|limited[- ]service|burger|pizza|restaurant|food service", "722513", "Limited-Service Restaurants"),
    (r"coffee|caf[eé]|bakery|bakeries", "722515", "Snack and Nonalcoholic Beverage Bars"),
    (r"bar\b|brewery|winery|distillery", "722410", "Drinking Places (Alcoholic Beverages)"),
    (r"catering", "722320", "Caterers"),
    (r"grocery|supermarket", "445110", "Supermarkets and Other Grocery Retailers"),
    (r"software|saas|cloud|app development|platform", "513210", "Software Publishers"),
    (r"it services|it consulting|computer systems design|managed services", "541512", "Computer Systems Design Services"),
    (r"custom software|web development|web design", "541511", "Custom Computer Programming Services"),
    (r"artificial intelligence|machine learning|data analytics", "541715", "R&D in the Physical, Engineering, and Life Sciences"),
    (r"biotech|pharmaceutical|life sciences", "541714", "Research and Development in Biotechnology"),
    (r"marketing|advertising|branding", "541810", "Advertising Agencies"),
    (r"accounting|bookkeeping|tax preparation", "541211", "Offices of Certified Public Accountants"),
    (r"law firm|legal services|attorneys?", "541110", "Offices of Lawyers"),
    (r"architect", "541310", "Architectural Services"),
    (r"engineering services|engineering firm", "541330", "Engineering Services"),
    (r"management consulting|consulting", "541611", "Administrative Management and General Management Consulting Services"),
    (r"staffing|recruiting|employment agency", "561311", "Employment Placement Agencies"),
    (r"construction|general contractor", "236220", "Commercial and Institutional Building Construction"),
    (r"plumbing|hvac|heating", "238220", "Plumbing, Heating, and Air-Conditioning Contractors"),
    (r"electrical contractor|electrician", "238210", "Electrical Contractors"),
    (r"real estate", "531210", "Offices of Real Estate Agents and Brokers"),
    (r"manufactur", "339999", "All Other Miscellaneous Manufacturing"),
    (r"eyewear|eyeglasses|optical|optometr", "456130", "Optical Goods Retailers"),
    (r"apparel|fashion|clothing", "458110", "Clothing and Clothing Accessories Retailers"),
    (r"e-?commerce|online retail", "455219", "All Other General Merchandise Retailers"),
    (r"retail|store", "459999", "All Other Miscellaneous Retailers"),
    (r"hotel|hospitality|lodging", "721110", "Hotels (except Casino Hotels) and Motels"),
    (r"fitness|gym", "713940", "Fitness and Recreational Sports Centers"),
    (r"salon|barber|spa\b", "812112", "Beauty Salons"),
    (r"dental|dentist", "621210", "Offices of Dentists"),
    (r"health ?care|clinic|medical", "621111", "Offices of Physicians (except Mental Health Specialists)"),
    (r"education|school|tutoring|training", "611710", "Educational Support Services"),
    (r"nonprofit|non-profit|charity", "813219", "Other Grantmaking and Giving Services"),
    (r"logistics|trucking|freight|delivery", "484110", "General Freight Trucking, Local"),
    (r"financial services|fintech|bank", "522320", "Financial Transactions Processing, Reserve, and Clearinghouse Activities"),
    (r"insurance", "524210", "Insurance Agencies and Brokerages"),
    (r"media|publishing|film|video production", "512110", "Motion Picture and Video Production"),
    (r"cleaning|janitorial", "561720", "Janitorial Services"),
)


def naics_guess(text: str) -> dict | None:
    lowered = text.lower()
    for pattern, code, title in _NAICS:
        if re.search(pattern, lowered):
            return {"code": code, "title": title}
    return None


_SUFFIXES = r"\b(the|inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|pllc|llp|lp|pc|p\.c|holdings?|group)\b\.?"


def name_key(name: str) -> str:
    """Comparable company name: lowercase, no legal suffixes or punctuation."""
    text = re.sub(r"&", " and ", name.lower())
    text = re.sub(_SUFFIXES, " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def name_similarity(a: str, b: str) -> float:
    """1.0 for the same name ignoring suffixes, else token overlap (Jaccard)."""
    ka, kb = name_key(a), name_key(b)
    if not ka or not kb:
        return 0.0
    if ka == kb:
        return 1.0
    ta, tb = set(ka.split()), set(kb.split())
    return len(ta & tb) / len(ta | tb)


def soql_prefix(name: str) -> str | None:
    """Uppercase name prefix safe to embed in a SoQL string literal, or None if too short."""
    cleaned = re.sub(r"[^A-Za-z0-9&' .-]", " ", name).upper()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()[:60]
    if len(cleaned.replace(" ", "")) < 3:
        return None
    return cleaned.replace("'", "''")


_LEGAL_ENDINGS = ("", " INC.", ", INC.", " INC", ", INC", " LLC", ", LLC", " L.L.C.", " CORP.", " CORPORATION", " CO.", " LTD.", " PLLC", " LLP")


def name_variants(name: str) -> list[str]:
    """Likely registry spellings of a name, SoQL-escaped: 'Acme Inc' -> 'ACME', 'ACME, INC.', ..."""
    base = soql_prefix(name)
    if not base:
        return []
    base = re.sub(r",?\s+(INC|INCORPORATED|LLC|L\.L\.C|CORP|CORPORATION|CO|LTD|PLLC|LLP)\.?$", "", base).strip(" ,")
    return [base + ending for ending in _LEGAL_ENDINGS] if len(base) >= 2 else []


def year(value) -> int | None:
    match = re.search(r"\b(1[89]\d{2}|20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None
