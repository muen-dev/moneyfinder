"""/live: one page that runs the whole demo flow (see business_research.live_demo) and shows it as it happens."""

import json
from pathlib import Path

from flask import abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from .. import live_demo

FILED = live_demo.REPO_DIR / "demo" / "gowanus-kettle" / "filled"  # demo_forms.py output

# The page polls its status (connect-src) and embeds Anchor's live view of the browser (frame-src).
CSP = (
    "default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self'; connect-src 'self'; "
    "frame-src 'self' https://live.anchorbrowser.io; form-action 'self'; base-uri 'none'; frame-ancestors 'self'"
)


def register(app) -> None:
    @app.get("/live")
    def live_start_page():
        return render_template("live.html", job_id=None, demo_email=next(iter(live_demo.DEMO_EMAILS)))

    @app.post("/live")
    def live_start():
        try:
            job_id = live_demo.start(request.form.get("email", ""))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("live_start_page"))
        return redirect(url_for("live_page", job_id=job_id))

    @app.get("/live/<job_id>")
    def live_page(job_id: str):
        job = live_demo.get(job_id) or abort(404)
        return render_template("live.html", job_id=job_id, demo_email=job["email"])

    @app.get("/live/<job_id>/status")
    def live_status(job_id: str):
        job = live_demo.get(job_id) or abort(404)
        job["screenshot"] = url_for("live_screenshot", job_id=job_id) if job.get("screenshot") else None
        job["pdf"] = url_for("live_pdf", job_id=job_id) if job.get("pdf") else None
        return jsonify(job)

    @app.get("/live/<job_id>/screenshot.png")
    def live_screenshot(job_id: str):
        job = live_demo.get(job_id) or abort(404)
        path = Path(job.get("screenshot") or "")
        if not job.get("screenshot") or not path.is_file():
            abort(404)
        return send_file(path, mimetype="image/png")

    @app.get("/live/<job_id>/IT-636.pdf")
    def live_pdf(job_id: str):
        job = live_demo.get(job_id) or abort(404)
        path = Path(job.get("pdf") or "")
        if not job.get("pdf") or not path.is_file():
            abort(404)
        return send_file(path, mimetype="application/pdf")

    @app.get("/live/filed")
    def live_filed():
        manifest = json.loads((FILED / "manifest.json").read_text())
        return render_template("filed.html", m=manifest, total=sum(f["amount"] for f in manifest["forms"]))

    @app.get("/live/filed/<code>.pdf")
    def live_filed_pdf(code: str):
        codes = {f["code"] for f in json.loads((FILED / "manifest.json").read_text())["forms"]}
        if code not in codes:
            abort(404)
        return send_file(FILED / f"{code}.pdf", mimetype="application/pdf")
