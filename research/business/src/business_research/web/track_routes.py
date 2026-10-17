"""Track path: claim-status UI (ui/domain.html) + shared /api/* from src.server.dispatch_api."""

from __future__ import annotations

from flask import Flask, jsonify, redirect, request, send_from_directory

from business_research.wallet import _repo

_repo.ensure_repo_on_path()

from src.server import UI_ENTRY, UI_ROOT, dispatch_api, ensure_seeded  # noqa: E402


def register(app: Flask) -> None:
    ensure_seeded()

    @app.get("/track/")
    def track():
        """Track path entry — blue claim-path UI (possible funds, tracker, evidence)."""
        return send_from_directory(UI_ENTRY.parent, UI_ENTRY.name)

    @app.get("/track")
    def track_noslash():
        return redirect("/track/", code=302)

    @app.get("/unclaimed/")
    def unclaimed_redirect():
        return redirect("/track/", code=302)

    @app.get("/unclaimed")
    def unclaimed_noslash():
        return redirect("/track/", code=302)

    @app.get("/track/landing")
    def track_landing():
        """Optional marketing landing (ui/index.html); product Track entry is /track/."""
        landing = UI_ROOT / "index.html"
        if not landing.exists():
            return redirect("/track/", code=302)
        return send_from_directory(landing.parent, landing.name)

    @app.route("/api/<path:rest>", methods=["GET", "POST", "OPTIONS"])
    def track_api(rest: str):
        if request.method == "OPTIONS":
            resp = app.make_response(("", 204))
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return resp
        path = "/api/" + rest
        body = None
        if request.method == "POST":
            body = request.get_json(silent=True)
            if body is None:
                body = {}
        query = {k: request.args.getlist(k) for k in request.args}
        status, value = dispatch_api(request.method, path, query, body)
        return jsonify(value), status
