"""Agentic PDF filler: an Anchor cloud browser opens the official NY Form IT-636 (Alcoholic Beverage Production
Credit, from tax.ny.gov) in a PDF viewer and fills its form fields from the business's dossier, one by one, so you
can watch. It saves the filled PDF, reads every field back from the saved file, and never submits anything.

    uv run --project kb --with playwright python form-filling/fill_pdf.py --slug gowanuskettle-example
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import httpx

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from fill import (OUT, REPO, START, anchor_key, create_session, end_session, fact_value, load_dossier, log,  # noqa: E402
                  mask_ein, masked, source_of)

PDFJS = "https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174"
FORM = {"code": "IT-636", "title": "IT-636 Alcoholic Beverage Production Credit (2025)",
        "url": "https://www.tax.ny.gov/pdf/current_forms/it/it636_fill_in.pdf", "file": "it636_fill_in.pdf"}
GALLONS_PER_BARREL = 31
BEER_RATE_FIRST_500K = 0.14  # IT-636 Schedule B line 3


def official_pdf() -> bytes:
    """The blank official form, cached under form-filling/out/forms/ (gitignored)."""
    path = OUT / "forms" / FORM["file"]
    if not path.is_file():
        r = httpx.get(FORM["url"], headers={"User-Agent": "Mozilla/5.0 (moneyfinder form filler)"}, timeout=30,
                      follow_redirects=True)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            raise SystemExit(f"{FORM['url']} did not return a PDF")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    return path.read_bytes()


def plan_it636(d: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Form fields in page order with value, label and provenance; fields with no source value go to needs_user."""
    b = d.get("business") or {}
    year = b.get("tax_year")
    legal, ein, addr = b.get("legal_name"), b.get("ein"), b.get("hq_address")
    barrels, _, barrels_src = fact_value(d, "ny_beer_barrels")
    sla, _, sla_src = fact_value(d, "sla_license_number")
    gallons = int(re.sub(r"\D", "", str(barrels))) * GALLONS_PER_BARREL if barrels else None
    line2 = min(gallons, 500_000) if gallons else None
    credit = round(line2 * BEER_RATE_FIRST_500K) if line2 else None
    src = {k: source_of(d, k, b.get(k)) for k in ("legal_name", "ein", "hq_address", "tax_year")}
    gal = f"{gallons:,}" if gallons else None
    rows = [
        # (field, label, value, kind, from, source)
        ("date_begin", "Tax period beginning", f"01/01/{year}" if year else None, "text", "business.tax_year", src["tax_year"]),
        ("date_end", "Tax period ending", f"12/31/{year}" if year else None, "text", "business.tax_year", src["tax_year"]),
        ("names_return", "Name(s) as shown on return", legal, "text", "business.legal_name", src["legal_name"]),
        ("ID_num", "Identifying number (EIN)", ein, "text", "business.ein", src["ein"]),
        ("lineA", "A. Partnership that earned the credit", "Yes" if legal else None, "check", "business.entity_type (LLC files IT-204)", "registry"),
        ("lineB", "B. Registered distributor (Article 18)", "Yes" if sla else None, "check", "facts.sla_license_number", sla_src),
        ("lineB_distributor", "Name of registered distributor", legal, "text", "business.legal_name", src["legal_name"]),
        ("lineB_EIN", "EIN of registered distributor", ein, "text", "business.ein", src["ein"]),
        ("lineB_SLA", "SLA license number", sla, "text", "facts.sla_license_number", sla_src),
        ("lineC1", "C. Produced beer in NYS", "Yes" if gallons else None, "check", "facts.ny_beer_barrels", barrels_src),
        ("lineC2", "C. Produced cider in NYS", "No", "check", "business.industry (brewery)", "registry"),
        ("lineC3", "C. Produced wine in NYS", "No", "check", "business.industry (brewery)", "registry"),
        ("lineC4", "C. Produced liquor in NYS", "No", "check", "business.industry (brewery)", "registry"),
        ("SchB_P1_A1", "Beer production facility address", addr, "text", "business.hq_address", src["hq_address"]),
        ("SchB_P1_B1", "Total gallons of beer", gal, "text", f"facts.ny_beer_barrels x {GALLONS_PER_BARREL}", barrels_src),
        ("line1", "1. Column B total", gal, "text", "Schedule B column B", "computed"),
        ("line2", "2. Lesser of line 1 or 500,000", f"{line2:,}" if line2 else None, "text", "line 1", "computed"),
        ("line3", "3. Credit, first 500,000 gallons (x .14)", f"{credit:,}" if credit else None, "text", "line 2 x .14", "computed"),
        ("line8", "8. Total beer production credit", f"{credit:,}" if credit else None, "text", "line 3 + line 7", "computed"),
    ]
    plan, needs_user = [], []
    for field, label, value, kind, frm, source in rows:
        if value in (None, ""):
            needs_user.append({"field": field, "label": label, "reason": f"no source value ({frm})"})
        else:
            plan.append({"field": field, "label": label, "value": str(value), "kind": kind, "from": frm,
                         "source": source or "dossier"})
    return plan, needs_user


VIEWER = """<!doctype html><html><head><meta charset="utf-8"><title>__FILE__</title>
<link rel="stylesheet" href="__PDFJS__/web/pdf_viewer.css">
<style>
  body { margin: 0; background: #525659; font: 13px system-ui, sans-serif; }
  #bar { position: fixed; inset: 0 0 auto 0; height: 40px; background: #323639; color: #f1f1f1; display: flex;
         align-items: center; gap: 18px; padding: 0 16px; z-index: 10; }
  #bar b { font-weight: 600; } #bar span { color: #bdc1c6; } #status { margin-left: auto; color: #ffd27a !important; }
  #viewerContainer { position: absolute; inset: 40px 0 0 0; overflow: auto; }
  .pdfViewer .page { margin: 14px auto; border: 0; box-shadow: 0 2px 10px rgba(0,0,0,.5); }
</style>
<script src="__PDFJS__/build/pdf.min.js"></script>
<script src="__PDFJS__/build/pdf.worker.min.js"></script>
<script src="__PDFJS__/web/pdf_viewer.js"></script>
</head><body>
<div id="bar"><b>__FILE__</b><span>__SOURCE__</span><span id="status">Opening</span></div>
<div id="viewerContainer"><div id="viewer" class="pdfViewer"></div></div>
<script>
pdfjsLib.GlobalWorkerOptions.workerSrc = "__PDFJS__/build/pdf.worker.min.js";
const container = document.getElementById("viewerContainer");
const eventBus = new pdfjsViewer.EventBus();
const linkService = new pdfjsViewer.PDFLinkService({ eventBus });
const viewer = new pdfjsViewer.PDFViewer({ container, eventBus, linkService,
  annotationMode: pdfjsLib.AnnotationMode.ENABLE_FORMS, textLayerMode: 0 });
linkService.setViewer(viewer);
eventBus.on("pagesinit", () => { viewer.currentScaleValue = "page-width"; });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const find = (id) => document.querySelector(`[data-element-id="${id}"]`);
window.mf = {
  status(text) { document.getElementById("status").textContent = text; },
  async load(b64) {
    const data = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const doc = await pdfjsLib.getDocument({ data }).promise;
    mf.doc = doc; viewer.setDocument(doc); linkService.setDocument(doc, null);
    const fields = await doc.getFieldObjects();
    return Object.fromEntries(Object.entries(fields || {}).map(([n, ws]) =>
      [n, ws.map((w) => ({ id: w.id, page: w.page, type: w.type, exportValues: w.exportValues }))]));
  },
  async goto(page, id) {
    for (let i = 0; i < 120; i++) {
      const el = find(id);
      if (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); await sleep(250); return true; }
      if (i % 10 === 0) viewer.scrollPageIntoView({ pageNumber: page + 1 });
      await sleep(50);
    }
    return false;
  },
  mark(el, on) {
    el.style.outline = on ? "3px solid #FFB000" : "2px solid #2BA84A";
    el.style.outlineOffset = "1px";
    el.style.boxShadow = on ? "0 0 0 6px rgba(255,176,0,.25)" : "none";
  },
  async type(id, text, delay) {
    const el = find(id); mf.mark(el, true); el.focus();
    el.value = ""; el.dispatchEvent(new Event("input", { bubbles: true }));
    for (const ch of text) {
      el.value += ch; el.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(delay);
    }
    el.dispatchEvent(new Event("change", { bubbles: true })); el.blur(); mf.mark(el, false);
    return el.value;
  },
  async check(id) {
    const el = find(id); mf.mark(el, true); await sleep(200);
    if (!el.checked) el.click();
    mf.mark(el, false);
    return el.checked;
  },
  async save() {
    const bytes = await mf.doc.saveDocument();
    const reread = await pdfjsLib.getDocument({ data: bytes.slice() }).promise;
    const fields = await reread.getFieldObjects();
    const values = {};
    for (const [name, ws] of Object.entries(fields || {})) {
      const v = ws.map((w) => w.value).find((v) => v !== undefined && v !== null && v !== "" && v !== "Off");
      values[name] = v === undefined ? "" : String(v);
    }
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return { b64: btoa(s), values };
  },
};
</script></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", default="gowanuskettle-example")
    ap.add_argument("--domain", help="dossier file fallback domain (default: slug with the last '-' as '.')")
    ap.add_argument("--hold", type=float, default=10, help="seconds to keep the session open for recording")
    ap.add_argument("--watch-delay", type=float, default=2.5, help="seconds for the live view to load before typing")
    ap.add_argument("--type-delay", type=int, default=25, help="ms per typed character")
    ap.add_argument("--no-open", action="store_true", help="don't open the live view in the local browser")
    args = ap.parse_args()
    domain = args.domain or (args.slug.rsplit("-", 1)[0] + "." + args.slug.rsplit("-", 1)[1]
                             if "-" in args.slug else args.slug)

    key = anchor_key()
    log(f"starting: slug={args.slug}, form {FORM['code']}; creating Anchor session, loading dossier and form in parallel")
    with ThreadPoolExecutor(3) as pool:
        session_f = pool.submit(create_session, key)
        dossier_f = pool.submit(load_dossier, args.slug, domain)
        pdf_f = pool.submit(official_pdf)
        session = session_f.result()
        sid, live = session.get("id"), session.get("live_view_url")
        log(f"Anchor session {sid}")
        print(f"\n  LIVE VIEW: {live}\n", flush=True)
        if live and not args.no_open:
            subprocess.run(["open", live], check=False)
        try:
            dossier, origin = dossier_f.result()
            blank = pdf_f.result()
        except BaseException:
            end_session(key, sid)
            raise

    receipt: dict[str, Any] = {}
    try:
        b = dossier.get("business") or {}
        log(f"dossier for {b.get('legal_name') or args.slug} from {origin}")
        log(f"official form {FORM['code']} from {FORM['url']} ({len(blank) // 1024} KB)")
        plan, needs_user = plan_it636(dossier)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(session["cdp_url"])
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_viewport_size({"width": 1100, "height": 900})
            html = (VIEWER.replace("__PDFJS__", PDFJS).replace("__FILE__", FORM["file"])
                    .replace("__SOURCE__", f"tax.ny.gov  ·  {FORM['title']}"))
            page.set_content(html, wait_until="load")
            fields = page.evaluate("b64 => mf.load(b64)", base64.b64encode(blank).decode())
            log(f"{FORM['code']} open in the cloud browser's PDF viewer: {len(fields)} form fields; "
                f"waiting {args.watch_delay:g}s for the live view")
            page.evaluate("t => mf.status(t)", "Agent is filling this form")
            time.sleep(args.watch_delay)

            mismatches = []
            for row in plan:
                widgets = fields.get(row["field"]) or []
                if row["kind"] == "check":
                    widgets = [w for w in widgets if w.get("exportValues") == row["value"]]
                if not widgets:
                    mismatches.append({"field": row["field"], "expected": masked(row["value"]), "pdf": "(no such field)"})
                    continue
                w = widgets[0]
                shown = masked(row["value"])
                log(f"filling {row['label']} <- {shown} (source: {row['source']}, {row['from']})")
                page.evaluate("([p, id]) => mf.goto(p, id)", [w["page"], w["id"]])
                if row["kind"] == "check":
                    page.evaluate("id => mf.check(id)", w["id"])
                else:
                    page.evaluate("([id, t, d]) => mf.type(id, t, d)", [w["id"], row["value"], args.type_delay])

            page.evaluate("t => mf.status(t)", "Filled. Saving and checking every field")
            saved = page.evaluate("() => mf.save()")
            for row in plan:
                got = saved["values"].get(row["field"], "")
                if got != row["value"]:
                    mismatches.append({"field": row["field"], "expected": masked(row["value"]), "pdf": masked(got)})
            page.evaluate("t => mf.status(t)", "Ready for your review. Not submitted.")
            first = fields[plan[0]["field"]][0] if plan else None
            if first:
                page.evaluate("([p, id]) => mf.goto(p, id)", [first["page"], first["id"]])

            OUT.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            pdf_path = OUT / f"{args.slug}-{FORM['code']}-{stamp}.pdf"
            pdf_path.write_bytes(base64.b64decode(saved["b64"]))
            shot = pdf_path.with_suffix(".png")
            page.screenshot(path=str(shot))
            log(f"screenshot {shot.relative_to(REPO)}")
            log(f"filled pdf {pdf_path.relative_to(REPO)}")

            receipt = {
                "schema": "moneyfinder.form_fill_receipt/v1",
                "slug": args.slug,
                "form": {k: FORM[k] for k in ("code", "title", "url")},
                "dossier_source": origin,
                "status": "pdf_mismatch" if mismatches else "ready_for_user_approval",
                "submitted": False,
                "filled": {r["field"]: {"label": r["label"], "value": masked(r["value"]), "from": r["from"],
                                        "source": r["source"]} for r in plan},
                "needs_user": needs_user,
                "mismatches": mismatches,
                "ein": mask_ein(str(b["ein"])) if b.get("ein") else None,
                "anchor_session_id": sid,
                "filled_pdf": str(pdf_path.relative_to(REPO)),
                "screenshot": str(shot.relative_to(REPO)),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            rpath = pdf_path.with_suffix(".json")
            rpath.write_text(json.dumps(receipt, indent=2) + "\n")
            log(f"receipt {rpath.relative_to(REPO)}")

            print()
            if mismatches:
                log("STOPPED: the saved PDF does not match the approved values:")
                for m in mismatches:
                    print(f"    {m['field']}: expected {m['expected']!r}, PDF has {m['pdf']!r}")
            else:
                log(f"readback clean: {len(plan)} fields filled, saved and verified in the PDF")
            if needs_user:
                log("needs user: " + ", ".join(f"{n['label']} ({n['reason']})" for n in needs_user))
            log("NOT submitted. Form is ready for user approval in the product UI.")
            log(f"total {time.monotonic() - START:.1f}s (before hold)")
            if args.hold > 0:
                log(f"holding the session open {args.hold:g}s for recording")
                time.sleep(args.hold)
            browser.close()
    finally:
        end_session(key, sid)
    log(f"done in {time.monotonic() - START:.1f}s")
    return 1 if receipt.get("mismatches") else 0


if __name__ == "__main__":
    sys.exit(main())
