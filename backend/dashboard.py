#!/usr/bin/env python3
"""
Prometheus Engineering Dashboard
---------------------------------
Single-page HTML dashboard served by FastAPI.
Fetches live data from the Prometheus API endpoints.
"""

from __future__ import annotations

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Prometheus Dashboard</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #1e293b;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --good: #4ade80;
      --warn: #facc15;
      --bad: #f87171;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      padding: 16px 24px;
      border-bottom: 1px solid #334155;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    header h1 { margin: 0; font-size: 18px; }
    header .badge {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 999px;
      background: #334155;
      color: var(--accent);
    }
    nav {
      display: flex;
      gap: 8px;
      padding: 12px 24px;
      border-bottom: 1px solid #334155;
      flex-wrap: wrap;
    }
    nav button {
      background: #334155;
      color: var(--text);
      border: none;
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
    }
    nav button:hover { background: #475569; }
    nav button.active { background: var(--accent); color: #0f172a; }
    main { padding: 24px; }
    .panel {
      background: var(--panel);
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .panel h2 { margin: 0 0 10px 0; font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .card { background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px; }
    .card .label { font-size: 12px; color: var(--muted); }
    .card .value { font-size: 22px; font-weight: 600; margin-top: 6px; }
    .card .value.ok { color: var(--good); }
    .card .value.warn { color: var(--warn); }
    .card .value.bad { color: var(--bad); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #334155; }
    th { color: var(--muted); font-weight: 500; }
    .muted { color: var(--muted); }
    pre {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      overflow: auto;
      font-size: 12px;
      max-height: 360px;
    }
    #status { font-size: 12px; color: var(--muted); }
  </style>
</head>
<body>
  <header>
    <h1>Prometheus Engineering Dashboard</h1>
    <div class="badge" id="version">loading</div>
  </header>
  <nav>
    <button data-section="overview" class="active">Overview</button>
    <button data-section="devices">Devices</button>
    <button data-section="knowledge">Knowledge</button>
    <button data-section="simulation">Simulation</button>
    <button data-section="firmware">Firmware</button>
    <button data-section="diagnostics">Diagnostics</button>
    <button data-section="recovery">Recovery</button>
    <button data-section="agents">Agents</button>
    <button data-section="plugins">Plugins</button>
    <button data-section="metrics">Metrics</button>
    <button data-section="logs">Logs</button>
    <button data-section="policies">Policies</button>
  </nav>
  <main>
    <div id="status">Loading...</div>
    <div id="content"></div>
  </main>

  <script>
    const API_BASE = window.location.origin;
    const content = document.getElementById('content');
    const status = document.getElementById('status');

    async function loadSection(section) {
      status.textContent = `Loading ${section}...`;
      try {
        const res = await fetch(`${API_BASE}/omega/dashboard/${section}`);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data = await res.json();
        render(section, data);
        status.textContent = `Loaded ${section}`;
      } catch (err) {
        status.textContent = `Failed to load ${section}: ${err.message}`;
        content.innerHTML = `<div class="panel"><pre>${err.message}</pre></div>`;
      }
    }

    function render(section, data) {
      if (section === 'overview') {
        content.innerHTML = `
          <div class="panel">
            <h2>Platform Overview</h2>
            <div class="grid">
              <div class="card"><div class="label">Platform</div><div class="value">${escape(data.platform || '-')}</div></div>
              <div class="card"><div class="label">Version</div><div class="value">${escape(data.version || '-')}</div></div>
              <div class="card"><div class="label">Status</div><div class="value ${statusClass(data.status)}">${escape(data.status || '-')}</div></div>
              <div class="card"><div class="label">Devices</div><div class="value">${escape(String(data.devices ?? 0))}</div></div>
              <div class="card"><div class="label">Sessions</div><div class="value">${escape(String(data.sessions ?? 0))}</div></div>
              <div class="card"><div class="label">Capabilities</div><div class="value">${escape(String(data.capabilities ?? 0))}</div></div>
              <div class="card"><div class="label">Plugins</div><div class="value">${escape(String(data.plugins ?? 0))}</div></div>
              <div class="card"><div class="label">Agents</div><div class="value">${escape(String(data.agents ?? 0))}</div></div>
            </div>
          </div>`;
        return;
      }
      content.innerHTML = `<div class="panel"><h2>${escape(section)}</h2><pre>${escape(JSON.stringify(data, null, 2))}</pre></div>`;
    }

    function statusClass(value) {
      if (value === 'ok') return 'ok';
      if (value === 'degraded' || value === 'warn') return 'warn';
      if (value === 'error' || value === 'critical') return 'bad';
      return '';
    }

    function escape(text) {
      const div = document.createElement('div');
      div.textContent = String(text);
      return div.innerHTML;
    }

    document.querySelectorAll('nav button').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadSection(btn.dataset.section);
      });
    });

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/omega/dashboard/overview`);
        const data = await res.json();
        document.getElementById('version').textContent = data.version || 'Prometheus';
      } catch {
        document.getElementById('version').textContent = 'Prometheus';
      }
      loadSection('overview');
    })();
  </script>
</body>
</html>
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


def mount_dashboard(app: FastAPI) -> None:
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard_page(request: Request) -> str:
        return HTML_TEMPLATE

    @app.get("/dashboard/{section}")
    async def dashboard_section(request: Request, section: str):
        from services.omega_service import OmegaService
        from core.container import ServiceContainer

        container: ServiceContainer = request.app.state.container
        omega = container.resolve("omega_service", OmegaService)
        return omega.get_dashboard(section)
