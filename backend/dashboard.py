#!/usr/bin/env python3
"""
Prometheus Engineering Dashboard
---------------------------------
Single-page HTML dashboard served by FastAPI.
Hermes-style: sidebar nav + KPI/status cards + live activity feed + health badges.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Prometheus Engineering OS</title>
  <style>
    :root {
      --bg: #211F1A;
      --surface: #2A2823;
      --surface-raised: #35312B;
      --accent: #5AB9EA;
      --text: #EDE7D9;
      --muted: #9A9384;
      --good: #4ade80;
      --warn: #facc15;
      --bad: #f87171;
      --border: #3D3932;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      min-height: 100vh;
    }
    aside {
      width: 240px;
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      position: fixed;
      height: 100vh;
      z-index: 10;
    }
    .wordmark {
      padding: 20px;
      font-size: 16px;
      font-weight: 700;
      color: var(--accent);
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--border);
    }
    nav { flex: 1; padding: 12px; }
    nav a {
      display: block;
      padding: 10px 12px;
      color: var(--text);
      text-decoration: none;
      border-radius: 6px;
      font-size: 13px;
      margin-bottom: 4px;
      transition: background 0.15s;
    }
    nav a:hover, nav a.active { background: var(--surface-raised); }
    .sidebar-footer {
      padding: 16px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--muted);
    }
    main {
      flex: 1;
      margin-left: 240px;
      padding: 24px;
      width: 100%;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    .topbar h1 { font-size: 20px; font-weight: 600; }
    .badge {
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--surface-raised);
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border: 1px solid var(--border);
    }
    .badge.ok { color: var(--good); border-color: var(--good); }
    .badge.warn { color: var(--warn); border-color: var(--warn); }
    .badge.bad { color: var(--bad); border-color: var(--bad); }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .kpi-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      transition: transform 0.15s, border-color 0.15s;
    }
    .kpi-card:hover { border-color: var(--accent); transform: translateY(-2px); }
    .kpi-label {
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .kpi-value {
      font-size: 22px;
      font-weight: 600;
    }
    .kpi-value.running { color: var(--accent); }
    .kpi-value.healthy { color: var(--good); }
    .kpi-value.active { color: var(--good); }
    .kpi-value.idle { color: var(--warn); }
    .kpi-value.stopped { color: var(--bad); }
    .section { display: none; }
    .section.active { display: block; }
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .panel h2 {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 12px;
    }
    .activity-list {
      max-height: 400px;
      overflow-y: auto;
      font-size: 13px;
    }
    .activity-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid var(--border);
    }
    .activity-item:last-child { border-bottom: none; }
    .activity-time { color: var(--muted); font-size: 11px; white-space: nowrap; margin-left: 12px; }
    .activity-type { color: var(--accent); font-weight: 500; }
    .activity-detail { color: var(--text); margin-right: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 500px; }
    pre {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      overflow: auto;
      font-size: 12px;
      max-height: 360px;
      color: var(--text);
    }
    @media (max-width: 768px) {
      aside { transform: translateX(-100%); transition: transform 0.3s; }
      aside.open { transform: translateX(0); }
      main { margin-left: 0; }
      .menu-toggle { display: block !important; }
    }
    .menu-toggle {
      display: none;
      position: fixed;
      top: 12px;
      left: 12px;
      z-index: 20;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <button class="menu-toggle" onclick="document.querySelector('aside').classList.toggle('open')">☰</button>
  <aside>
    <div class="wordmark">PROMETHEUS</div>
    <nav>
      <a href="#" class="active" data-page="overview">Overview</a>
      <a href="#" data-page="kernel">Kernel</a>
      <a href="#" data-page="knowledge">Knowledge</a>
      <a href="#" data-page="simulation">Simulation</a>
      <a href="#" data-page="reasoning">Reasoning</a>
      <a href="#" data-page="hardware">Hardware</a>
      <a href="#" data-page="devices">Devices</a>
      <a href="#" data-page="agents">Agents</a>
      <a href="#" data-page="plugins">Plugins</a>
      <a href="#" data-page="activity">Activity Feed</a>
    </nav>
    <div class="sidebar-footer">
      <div id="version">v0.6.0</div>
      <div>Prometheus Engineering OS</div>
    </div>
  </aside>
  <main>
    <div class="topbar">
      <h1 id="page-title">Overview</h1>
      <span class="badge" id="health-badge">Checking...</span>
    </div>

    <section id="page-overview" class="section active">
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Kernel</div>
          <div class="kpi-value" id="kpi-kernel">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Knowledge</div>
          <div class="kpi-value" id="kpi-knowledge">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Simulation</div>
          <div class="kpi-value" id="kpi-simulation">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Reasoning</div>
          <div class="kpi-value" id="kpi-reasoning">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Hardware</div>
          <div class="kpi-value" id="kpi-hardware">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Connected Devices</div>
          <div class="kpi-value" id="kpi-devices">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Agents</div>
          <div class="kpi-value" id="kpi-agents">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Plugins</div>
          <div class="kpi-value" id="kpi-plugins">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Capabilities</div>
          <div class="kpi-value" id="kpi-capabilities">-</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Knowledge Facts</div>
          <div class="kpi-value" id="kpi-facts">-</div>
        </div>
      </div>
    </section>

    <section id="page-activity" class="section">
      <div class="panel">
        <h2>Live Activity Feed</h2>
        <div class="activity-list" id="activity-list">
          <div class="activity-item"><span class="activity-detail">Waiting for events...</span></div>
        </div>
      </div>
    </section>

    <section id="page-kernel" class="section">
      <div class="panel"><pre id="kernel-status">Loading...</pre></div>
    </section>
    <section id="page-knowledge" class="section">
      <div class="panel"><pre>Knowledge engine details loading...</pre></div>
    </section>
    <section id="page-simulation" class="section">
      <div class="panel"><pre>Simulation engine not registered in bootstrap (Idle)</pre></div>
    </section>
    <section id="page-reasoning" class="section">
      <div class="panel"><pre id="reasoning-status">Loading...</pre></div>
    </section>
    <section id="page-hardware" class="section">
      <div class="panel"><pre id="hardware-status">Loading...</pre></div>
    </section>
    <section id="page-devices" class="section">
      <div class="panel"><pre id="devices-status">Loading...</pre></div>
    </section>
    <section id="page-agents" class="section">
      <div class="panel"><pre id="agents-status">Loading...</pre></div>
    </section>
    <section id="page-plugins" class="section">
      <div class="panel"><pre id="plugins-status">Loading...</pre></div>
    </section>
  </main>

  <script>
    const API = window.location.origin;
    let eventSource;

    function showPage(name) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
      const el = document.getElementById('page-' + name);
      if (el) el.classList.add('active');
      document.querySelector('nav a[data-page="' + name + '"]')?.classList.add('active');
      document.getElementById('page-title').textContent = name.charAt(0).toUpperCase() + name.slice(1);
      if (name === 'activity') startEventStream();
      else stopEventStream();
      loadPageData(name);
    }

    document.querySelectorAll('nav a').forEach(a => {
      a.addEventListener('click', e => { e.preventDefault(); showPage(a.dataset.page); });
    });

    async function loadPageData(name) {
      if (name === 'kernel') {
        try {
          const res = await fetch(API + '/core/status');
          const data = await res.json();
          document.getElementById('kernel-status').textContent = JSON.stringify(data, null, 2);
        } catch (e) {
          document.getElementById('kernel-status').textContent = 'Failed to load: ' + e.message;
        }
      }
      if (name === 'devices') {
        try {
          const res = await fetch(API + '/devices');
          const data = await res.json();
          document.getElementById('devices-status').textContent = JSON.stringify(data, null, 2);
        } catch (e) {
          document.getElementById('devices-status').textContent = 'Failed to load: ' + e.message;
        }
      }
      if (name === 'agents') {
        try {
          const res = await fetch(API + '/health');
          const data = await res.json();
          document.getElementById('agents-status').textContent = JSON.stringify(data.agents_loaded, null, 2);
        } catch (e) {
          document.getElementById('agents-status').textContent = 'Failed to load: ' + e.message;
        }
      }
      if (name === 'plugins') {
        try {
          const res = await fetch(API + '/health');
          const data = await res.json();
          document.getElementById('plugins-status').textContent = JSON.stringify(data.plugins_loaded, null, 2);
        } catch (e) {
          document.getElementById('plugins-status').textContent = 'Failed to load: ' + e.message;
        }
      }
    }

    async function loadHealth() {
      try {
        const res = await fetch(API + '/status');
        const data = await res.json();
        const status = data.kernel ? (data.kernel === 'Running' ? 'ok' : 'stopped') : 'unknown';
        const badge = document.getElementById('health-badge');
        badge.textContent = (data.kernel || 'unknown').toUpperCase();
        badge.className = 'badge ' + (status === 'ok' ? 'ok' : status === 'stopped' ? 'bad' : 'warn');

        setKpi('kernel', data.kernel || '-', data.kernel ? data.kernel.toLowerCase() : '');
        setKpi('knowledge', data.knowledge || '-', data.knowledge ? data.knowledge.toLowerCase() : '');
        setKpi('simulation', data.simulation || '-', data.simulation ? data.simulation.toLowerCase() : '');
        setKpi('reasoning', data.reasoning || '-', data.reasoning ? data.reasoning.toLowerCase() : '');
        setKpi('hardware', data.hardware || '-', data.hardware ? data.hardware.toLowerCase() : '');
        setKpi('devices', String(data.devices ?? 0), '');
        setKpi('agents', String(data.agents ?? 0), '');
        setKpi('plugins', String(data.plugins ?? 0), '');
        setKpi('capabilities', String(data.capabilities ?? 0), '');
        setKpi('facts', String(data.knowledge_facts ?? 0), '');
      } catch (e) {
        console.error('Status fetch failed', e);
      }
    }

    function setKpi(id, text, cls) {
      const el = document.getElementById('kpi-' + id);
      if (!el) return;
      el.textContent = text;
      el.className = 'kpi-value' + (cls ? ' ' + cls : '');
    }

    function startEventStream() {
      if (eventSource) return;
      const list = document.getElementById('activity-list');
      list.innerHTML = '';
      eventSource = new EventSource(API + '/events');
      eventSource.onmessage = (ev) => {
        const item = document.createElement('div');
        item.className = 'activity-item';
        const data = JSON.parse(ev.data);
        const time = new Date(data.timestamp).toLocaleTimeString();
        item.innerHTML = '<div><span class="activity-type">' + escape(data.type) + '</span><span class="activity-detail">' + escape(JSON.stringify(data.data)) + '</span></div><span class="activity-time">' + escape(time) + '</span>';
        list.insertBefore(item, list.firstChild);
        if (list.children.length > 100) list.removeChild(list.lastChild);
      };
      eventSource.onerror = () => { eventSource.close(); };
    }

    function stopEventStream() {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    }

    function escape(text) {
      const div = document.createElement('div');
      div.textContent = String(text);
      return div.innerHTML;
    }

    loadHealth();
    setInterval(loadHealth, 5000);
  </script>
</body>
</html>
"""


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
