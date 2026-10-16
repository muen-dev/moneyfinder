"""Fill the official tax.ny.gov / irs.gov PDFs for the synthetic demo business, for the "ready to file" page.

All values are demo data for Gowanus Kettle Brewing Co. LLC (synthetic). SSNs are masked. Writes the filled PDFs
and manifest.json to demo/gowanus-kettle/filled/.

    uv run --no-project --with pypdf --with httpx python form-filling/demo_forms.py
"""

import json
from pathlib import Path

import httpx
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "demo" / "gowanus-kettle" / "filled"
CACHE = Path(__file__).resolve().parent / "out" / "forms"
NAME, EIN, ADDR = "Gowanus Kettle Brewing Co. LLC", "00-4271985", "417 Sackett Street, Brooklyn, NY 11231"

FORMS = [
    {
        "code": "IT-636", "agency": "NYS Department of Taxation and Finance",
        "title": "Alcoholic Beverage Production Credit", "amount": 13471,
        "basis": "3,104 barrels (96,224 gallons) of beer brewed in NY in 2025 x $0.14",
        "url": "https://www.tax.ny.gov/pdf/current_forms/it/it636_fill_in.pdf",
        "fields": {
            "date_begin": "01/01/2025", "date_end": "12/31/2025", "names_return": NAME, "ID_num": EIN,
            "lineA": "/Yes", "lineB": "/Yes", "lineB_distributor": NAME, "lineB_EIN": EIN, "lineB_SLA": "1319027",
            "lineC1": "/Yes", "lineC2": "/No", "lineC3": "/No", "lineC4": "/No",
            "SchB_P1_A1": ADDR, "SchB_P1_B1": "96,224", "line1": "96,224", "line2": "96,224",
            "line3": "13,471", "line8": "13,471",
        },
    },
    {
        "code": "IT-212", "agency": "NYS Department of Taxation and Finance",
        "title": "Investment Credit", "amount": 7460,
        "basis": "Canning line, $186,500, placed in service July 28, 2025 x 4%",
        "url": "https://www.tax.ny.gov/pdf/current_forms/it/it212_fill_in.pdf",
        "fields": {
            "names": NAME, "type of business": "Brewery (manufacturing)", "id number": EIN,
            "business began": "03/11/2019", "location of prop": ADDR, "NAICS code": "312120",
            "1 dollars": "7,460", "9 dollars": "7,460", "11 dollars": "7,460", "13 dollars": "7,460",
            "15a dollars": "7,460",
        },
    },
    {
        "code": "IT-643", "agency": "NYS Department of Taxation and Finance",
        "title": "Hire a Veteran Credit", "amount": 15075,
        "basis": "Two qualified veterans hired in 2025, 15% of first-year wages",
        "url": "https://www.tax.ny.gov/pdf/current_forms/it/it643_fill_in.pdf",
        "fields": {
            "Name": NAME, "ID_num": EIN, "LineA": "/Yes", "LineB": EIN, "LineC": "2", "LineD": "/Yes",
            "P1_First nameRow1": "Darnell", "P1_MIRow1": "R", "P1_Last nameRow1": "Hughes",
            "P1__SSN1": "XXX-XX-4417", "P1_Emp_periodRow1": "03/17/25-12/31/25", "P1_Wages1": "52,000",
            "P1_ColE1": "7,800", "P1_ColF1": "7,800",
            "P1_First nameRow2": "Keisha", "P1_MIRow2": "M", "P1_Last nameRow2": "Ortiz",
            "P1__SSN2": "XXX-XX-2093", "P1_Emp_periodRow2": "05/05/25-12/31/25", "P1_Wages2": "48,500",
            "P1_ColE2": "7,275", "P1_ColF2": "7,275",
            "Line1a": "15,075", "Line1": "15,075",
        },
    },
    {
        "code": "8846", "agency": "Internal Revenue Service",
        "title": "Credit for Employer Social Security and Medicare Taxes Paid on Certain Employee Tips",
        "amount": 9731, "basis": "Taproom tips $148,600; $127,200 creditable x 7.65%",
        "url": "https://www.irs.gov/pub/irs-pdf/f8846.pdf",
        "fields": {
            "f1_1[0]": NAME, "f1_2[0]": EIN, "f1_3[0]": "148,600", "f1_4[0]": "21,400", "f1_5[0]": "127,200",
            "f1_6[0]": "9,731", "f1_8[0]": "9,731",
        },
    },
]


def blank(url: str) -> Path:
    path = CACHE / Path(url).name
    if not path.is_file():
        r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (moneyfinder)"}, timeout=30, follow_redirects=True)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path


def short(name) -> str:
    return str(name).split(".")[-1]


def fill(src: Path, values: dict[str, str], dest: Path) -> list[str]:
    writer = PdfWriter(clone_from=PdfReader(src))
    texts = {k: v for k, v in values.items() if not v.startswith("/")}
    checks = {k: v for k, v in values.items() if v.startswith("/")}
    found = set()
    for page in writer.pages:
        names = set()
        for a in page.get("/Annots") or []:
            a = a.get_object()
            parent = a.get("/Parent").get_object() if a.get("/Parent") else None
            name = short(a.get("/T") or (parent or {}).get("/T") or "")
            names.add(name)
            if name in checks:  # mark the widget whose "on" state matches; the others go Off
                states = list((a.get("/AP") or {}).get("/N", {}).keys())
                on = checks[name] in states
                a[NameObject("/AS")] = NameObject(checks[name] if on else "/Off")
                (parent or a)[NameObject("/V")] = NameObject(checks[name])
                found.add(name)
        page_texts = {k: v for k, v in texts.items() if k in names}
        if page_texts:
            writer.update_page_form_field_values(page, page_texts, auto_regenerate=False)
            found |= set(page_texts)
    writer.set_need_appearances_writer(True)
    with dest.open("wb") as f:
        writer.write(f)
    return sorted(set(values) - found)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for form in FORMS:
        dest = OUT / f"{form['code']}.pdf"
        missing = fill(blank(form["url"]), form["fields"], dest)
        if missing:
            raise SystemExit(f"{form['code']}: no such fields {missing}")
        manifest.append({k: form[k] for k in ("code", "agency", "title", "amount", "basis", "url")}
                        | {"file": dest.name, "fields": len(form["fields"])})
        print(f"{form['code']}: {len(form['fields'])} fields -> {dest.relative_to(REPO)}")
    (OUT / "manifest.json").write_text(json.dumps({"business": NAME, "tax_year": 2025, "forms": manifest}, indent=2) + "\n")


if __name__ == "__main__":
    main()
