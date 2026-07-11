"""
Prometheus Dashboard — Vite SPA Mount
-------------------------------------
Serves the built Vite frontend from web/dist at the /dashboard route.
In development, Vite's dev server proxies API calls to this backend.
"""

import os
import sys

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse

if getattr(sys, "_MEIPASS", None):
    # Running as a PyInstaller-frozen sidecar: web/dist is bundled next to the exe.
    DIST_DIR = os.path.join(sys._MEIPASS, "web", "dist")
else:
    DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
INDEX_HTML = os.path.join(DIST_DIR, "index.html")


def mount_dashboard(app: FastAPI) -> None:
    assets_dir = os.path.join(DIST_DIR, "assets")

    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    def dashboard_root(request: Request):
        spa = request.query_params.get("spa")
        if spa == "false":
            return HTMLResponse("<h1>Dashboard SPA not built</h1><p>Run <code>cd web && npm run build</code></p>")
        if os.path.exists(INDEX_HTML):
            return FileResponse(INDEX_HTML)
        return HTMLResponse("<h1>Dashboard SPA not built</h1><p>Run <code>cd web && npm run build</code></p>")

    if os.path.isdir(assets_dir):
        from fastapi.staticfiles import StaticFiles
        app.mount("/dashboard/assets", StaticFiles(directory=assets_dir), name="dashboard-assets")

    @app.get("/dashboard/{path:path}", response_class=HTMLResponse, include_in_schema=False)
    def dashboard_fallback(request: Request, path: str):
        spa = request.query_params.get("spa")
        if spa == "false":
            return HTMLResponse("<h1>Not Found</h1>")
        if os.path.exists(INDEX_HTML):
            return FileResponse(INDEX_HTML)
        return HTMLResponse("<h1>Dashboard SPA not built</h1><p>Run <code>cd web && npm run build</code></p>")
