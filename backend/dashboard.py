#!/usr/bin/env python3
"""
Prometheus Engineering Dashboard
---------------------------------
Industrial terminal + sci-fi engineering aesthetic.
Mission control for engineering intelligence.
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
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0D1117;
      --surface: #161B22;
      --surface-raised: #1C2333;
      --border: #2A3441;
      --accent: #4DA3FF;
      --accent-dim: #2D6FB8;
      --good: #37D67A;
      --warn: #F5B041;
      --bad: #FF5C5C;
      --text: #F3F5F7;
      --muted: #9AA4B2;
      --font: 'IBM Plex Mono', 'Fira Code', 'JetBrains Mono', monospace;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; }
    body {
      font-family: var(--font);
      background: var(--bg);
      color: var(--text);
      font-size: 13px;
      line-height: 1.5;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    #boot-screen {
      position: fixed;
      inset: 0;
      background: var(--bg);
      z-index: 9999;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-family: var(--font);
      transition: opacity 0.6s ease;
    }
    #boot-screen.hidden {
      opacity: 0;
      pointer-events: none;
    }
    #boot-logo {
      color: var(--accent);
      font-size: 11px;
      line-height: 1.2;
      text-align: center;
      margin-bottom: 32px;
      white-space: pre;
      animation: bootPulse 2s ease-in-out infinite;
    }
    @keyframes bootPulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }
    #boot-steps {
      width: 320px;
      color: var(--muted);
      font-size: 12px;
    }
    .boot-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .boot-bar {
      height: 4px;
      background: var(--border);
      margin-top: 4px;
      position: relative;
      overflow: hidden;
    }
    .boot-bar-fill {
      position: absolute;
      inset: 0;
      background: var(--accent);
      width: 0%;
      transition: width 0.3s ease;
    }
    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }
    .cursor {
      display: inline-block;
      width: 8px;
      height: 14px;
      background: var(--accent);
      animation: blink 1s step-end infinite;
      vertical-align: middle;
      margin-left: 4px;
    }

    #app {
      display: flex;
      flex: 1;
      height: 100vh;
      overflow: hidden;
    }

    aside {
      width: 220px;
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .sidebar-header {
      padding: 16px;
      border-bottom: 1px solid var(--border);
    }
    .logo {
      color: var(--accent);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.12em;
      line-height: 1.3;
      white-space: pre;
    }
    nav { flex: 1; padding: 8px; overflow-y: auto; }
    nav a {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      color: var(--muted);
      text-decoration: none;
      font-size: 12px;
      border-left: 2px solid transparent;
      transition: color 0.15s, border-color 0.15s;
      cursor: pointer;
    }
    nav a:hover { color: var(--text); border-left-color: var(--border); }
    nav a.active { color: var(--text); border-left-color: var(--accent); background: var(--surface-raised); }
    .nav-icon {
      width: 16px;
      text-align: center;
      font-size: 10px;
      color: var(--accent-dim);
    }
    nav a.active .nav-icon { color: var(--accent); }
    .sidebar-footer {
      padding: 12px 16px;
      border-top: 1px solid var(--border);
      font-size: 10px;
      color: var(--muted);
      line-height: 1.6;
    }

    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 20px;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
      flex-shrink: 0;
    }
    .topbar h1 {
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .status-badges {
      display: flex;
      gap: 16px;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
    }
    .status-badges span { display: flex; align-items: center; gap: 6px; }
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--muted);
      display: inline-block;
    }
    .dot.ok { background: var(--good); box-shadow: 0 0 6px var(--good); }
    .dot.warn { background: var(--warn); box-shadow: 0 0 6px var(--warn); }
    .dot.bad { background: var(--bad); box-shadow: 0 0 6px var(--bad); }
    .dot.idle { background: var(--muted); }

    .content {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
    }
    .section { display: none; }
    .section.active { display: block; }

    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 14px;
      margin-bottom: 12px;
    }
    .panel-title {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--muted);
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .kpi-panel {
      background: var(--surface);
      border: 1px solid var(--border);
      padding: 12px;
      position: relative;
    }
    .kpi-panel::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--accent-dim), transparent);
      opacity: 0;
      transition: opacity 0.3s;
    }
    .kpi-panel:hover::before { opacity: 1; }
    .kpi-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .kpi-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }
    .kpi-value {
      font-size: 18px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
    .kpi-value.running { color: var(--accent); }
    .kpi-value.healthy { color: var(--good); }
    .kpi-value.active { color: var(--good); }
    .kpi-value.idle { color: var(--warn); }
    .kpi-value.stopped { color: var(--bad); }
    .kpi-value.count { color: var(--text); }
    .kpi-sub {
      font-size: 10px;
      color: var(--muted);
      margin-top: 4px;
    }

    .activity-list {
      max-height: 500px;
      overflow-y: auto;
      font-size: 12px;
    }
    .activity-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--border);
    }
    .activity-item:last-child { border-bottom: none; }
    .activity-time { color: var(--muted); font-size: 10px; white-space: nowrap; margin-left: 12px; }
    .activity-type { color: var(--accent); font-weight: 500; }
    .activity-detail { color: var(--text); margin-right: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 600px; }

    pre {
      background: var(--bg);
      border: 1px solid var(--border);
      padding: 12px;
      overflow: auto;
      font-size: 11px;
      max-height: 500px;
      color: var(--text);
      line-height: 1.6;
    }

    .bottom-bar {
      border-top: 1px solid var(--border);
      background: var(--surface);
      padding: 8px 20px;
      display: flex;
      gap: 24px;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      flex-shrink: 0;
    }
    .bottom-bar .value { color: var(--text); margin-left: 6px; }

    .menu-toggle {
      display: none;
      position: fixed;
      top: 10px;
      left: 10px;
      z-index: 20;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 10px;
      cursor: pointer;
      font-size: 16px;
    }

    @media (max-width: 768px) {
      aside { transform: translateX(-100%); transition: transform 0.2s ease; position: fixed; height: 100vh; z-index: 15; }
      aside.open { transform: translateX(0); }
      main { margin-left: 0; }
      .menu-toggle { display: block; }
      .content { padding: 12px; }
      .kpi-grid { grid-template-columns: 1fr; }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .fade-in { animation: fadeIn 0.3s ease forwards; }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .pulse { animation: pulse 2s ease-in-out infinite; }

    .graph-canvas {
      width: 100%;
      height: 300px;
      background: var(--bg);
      border: 1px solid var(--border);
      position: relative;
      overflow: hidden;
    }
    .graph-node {
      position: absolute;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 6px var(--accent);
      transform: translate(-50%, -50%);
    }
    .graph-edge {
      position: absolute;
      height: 1px;
      background: var(--accent-dim);
      transform-origin: left center;
      opacity: 0.4;
    }
  </style>
</head>
<body>
  <div id="boot-screen">
    <div id="boot-logo">
        ▲
       ▲▲▲
      ▲ ● ▲
       ▲▲▲
        ▲
    </div>
    <div id="boot-steps">
      <div class="boot-row"><span>Initializing Kernel</span><span id="boot-pct-1">0%</span></div>
      <div class="boot-bar"><div class="boot-bar-fill" id="boot-fill-1"></div></div>
      <div class="boot-row" style="margin-top:8px"><span>Loading Knowledge Graph</span><span id="boot-pct-2">0%</span></div>
      <div class="boot-bar"><div class="boot-bar-fill" id="boot-fill-2"></div></div>
      <div class="boot-row" style="margin-top:8px"><span>Mounting Engines</span><span id="boot-pct-3">0%</span></div>
      <div class="boot-bar"><div class="boot-bar-fill" id="boot-fill-3"></div></div>
      <div class="boot-row" style="margin-top:12px; color: var(--accent);" id="boot-ready">BOOT SEQUENCE COMPLETE<span class="cursor"></span></div>
    </div>
  </div>

  <div id="app" style="display:none;">
    <button class="menu-toggle" onclick="document.querySelector('aside').classList.toggle('open')">☰</button>
    <aside>
      <div class="sidebar-header">
        <div class="logo">
PROMETHEUS
Engineering OS v0.6.0</div>
      </div>
      <nav>
        <a href="#" class="active" data-page="overview"><span class="nav-icon">◈</span> MISSION CONTROL</a>
        <a href="#" data-page="kernel"><span class="nav-icon">◆</span> Kernel</a>
        <a href="#" data-page="knowledge"><span class="nav-icon">◈</span> Knowledge</a>
        <a href="#" data-page="simulation"><span class="nav-icon">◇</span> Simulation</a>
        <a href="#" data-page="reasoning"><span class="nav-icon">⬡</span> Reasoning</a>
        <a href="#" data-page="capabilities"><span class="nav-icon">⬢</span> Capabilities</a>
        <a href="#" data-page="hardware"><span class="nav-icon">⬣</span> Hardware</a>
        <a href="#" data-page="devices"><span class="nav-icon">◉</span> Devices</a>
        <a href="#" data-page="agents"><span class="nav-icon">◎</span> Agents</a>
        <a href="#" data-page="plugins"><span class="nav-icon">◈</span> Plugins</a>
        <a href="#" data-page="events"><span class="nav-icon">◐</span> Events</a>
      </nav>
      <div class="sidebar-footer">
        <div style="color:var(--accent);">PROMETHEUS</div>
        <div>Engineering Intelligence OS</div>
        <div style="margin-top:4px;" id="uptime">Uptime: 0s</div>
      </div>
    </aside>

    <main>
      <div class="topbar">
        <h1 id="page-title">Mission Control</h1>
        <div class="status-badges">
          <span><span class="dot" id="dot-kernel"></span> <span id="label-kernel">Kernel</span></span>
          <span><span class="dot" id="dot-knowledge"></span> <span id="label-knowledge">Knowledge</span></span>
          <span><span class="dot" id="dot-simulation"></span> <span id="label-simulation">Simulation</span></span>
          <span><span class="dot" id="dot-reasoning"></span> <span id="label-reasoning">Reasoning</span></span>
          <span><span class="dot" id="dot-hardware"></span> <span id="label-hardware">Hardware</span></span>
        </div>
      </div>

      <div class="content">
        <section id="page-overview" class="section active">
          <div class="panel">
            <div class="panel-title"><span>OVERVIEW</span><span id="overview-time">--</span></div>
            <div class="kpi-grid">
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Kernel</span><span class="dot" id="kpi-kernel-dot"></span></div>
                <div class="kpi-value" id="kpi-kernel">--</div>
                <div class="kpi-sub">Health</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Knowledge</span><span class="dot" id="kpi-knowledge-dot"></span></div>
                <div class="kpi-value" id="kpi-knowledge">--</div>
                <div class="kpi-sub">Graph</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Simulation</span><span class="dot" id="kpi-simulation-dot"></span></div>
                <div class="kpi-value" id="kpi-simulation">--</div>
                <div class="kpi-sub">Engine</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Reasoning</span><span class="dot" id="kpi-reasoning-dot"></span></div>
                <div class="kpi-value" id="kpi-reasoning">--</div>
                <div class="kpi-sub">Store</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Hardware</span><span class="dot" id="kpi-hardware-dot"></span></div>
                <div class="kpi-value" id="kpi-hardware">--</div>
                <div class="kpi-sub">HAL</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Devices</span></div>
                <div class="kpi-value count" id="kpi-devices">--</div>
                <div class="kpi-sub">Connected</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Agents</span></div>
                <div class="kpi-value count" id="kpi-agents">--</div>
                <div class="kpi-sub">Registered</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Plugins</span></div>
                <div class="kpi-value count" id="kpi-plugins">--</div>
                <div class="kpi-sub">Loaded</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Capabilities</span></div>
                <div class="kpi-value count" id="kpi-capabilities">--</div>
                <div class="kpi-sub">Discovered</div>
              </div>
              <div class="kpi-panel">
                <div class="kpi-header"><span class="kpi-label">Knowledge Facts</span></div>
                <div class="kpi-value count" id="kpi-facts">--</div>
                <div class="kpi-sub">Asserted</div>
              </div>
            </div>
          </div>
        </section>

        <section id="page-kernel" class="section">
          <div class="panel"><pre id="kernel-status">Loading...</pre></div>
        </section>
        <section id="page-knowledge" class="section">
          <div class="panel">
            <div class="panel-title"><span>KNOWLEDGE GRAPH</span><span id="knowledge-count">--</span></div>
            <div class="graph-canvas" id="knowledge-graph"></div>
            <pre id="knowledge-status" style="margin-top:10px;">Loading...</pre>
          </div>
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
        <section id="page-capabilities" class="section">
          <div class="panel"><pre id="capabilities-status">Loading...</pre></div>
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
        <section id="page-events" class="section">
          <div class="panel">
            <div class="panel-title"><span>LIVE EVENT STREAM</span><span class="pulse" style="color:var(--good);">● LIVE</span></div>
            <div class="activity-list" id="activity-list">
              <div class="activity-item"><span class="activity-detail">Waiting for events...</span></div>
            </div>
          </div>
        </section>
      </div>

      <div class="bottom-bar">
        <span>Kernel:<span class="value" id="bar-kernel">--</span></span>
        <span>Devices:<span class="value" id="bar-devices">--</span></span>
        <span>Agents:<span class="value" id="bar-agents">--</span></span>
        <span>Knowledge:<span class="value" id="bar-knowledge">--</span></span>
        <span>Latency:<span class="value" id="bar-latency">--</span></span>
        <span style="margin-left:auto;" id="bar-version">v0.6.0</span>
      </div>
    </main>
  </div>

  <script>
    const API = window.location.origin;
    let eventSource;
    let bootComplete = false;

    function bootOverlay() {
      const steps = [
        { fill: 'boot-fill-1', pct: 'boot-pct-1', target: 100, delay: 400 },
        { fill: 'boot-fill-2', pct: 'boot-pct-2', target: 100, delay: 600 },
        { fill: 'boot-fill-3', pct: 'boot-pct-3', target: 100, delay: 500 },
      ];
      let i = 0;
      function runStep() {
        if (i >= steps.length) {
          setTimeout(() => {
            document.getElementById('boot-screen').classList.add('hidden');
            document.getElementById('app').style.display = 'flex';
            bootComplete = true;
            init();
          }, 400);
          return;
        }
        const step = steps[i];
        const fill = document.getElementById(step.fill);
        const pct = document.getElementById(step.pct);
        let progress = 0;
        const interval = setInterval(() => {
          progress += Math.floor(Math.random() * 12) + 4;
          if (progress >= step.target) {
            progress = step.target;
            clearInterval(interval);
            i++;
            setTimeout(runStep, 150);
          }
          fill.style.width = progress + '%';
          pct.textContent = progress + '%';
        }, 60);
      }
      setTimeout(runStep, 300);
    }

    function showPage(name) {
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
      const el = document.getElementById('page-' + name);
      if (el) el.classList.add('active');
      document.querySelector('nav a[data-page="' + name + '"]')?.classList.add('active');
      const titles = {
        overview: 'Mission Control',
        kernel: 'Kernel Status',
        knowledge: 'Knowledge Graph',
        simulation: 'Simulation Engine',
        reasoning: 'Reasoning Engine',
        capabilities: 'Capabilities',
        hardware: 'Hardware Interface',
        devices: 'Device Registry',
        agents: 'Agent Registry',
        plugins: 'Plugin Registry',
        events: 'Live Events',
      };
      document.getElementById('page-title').textContent = titles[name] || name;
      if (name === 'events') startEventStream();
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
          if (Array.isArray(data)) {
            document.getElementById('devices-status').textContent = data.map(d => JSON.stringify(d, null, 2)).join('\\n---\\n');
          } else {
            document.getElementById('devices-status').textContent = JSON.stringify(data, null, 2);
          }
        } catch (e) {
          document.getElementById('devices-status').textContent = 'Failed to load: ' + e.message;
        }
      }
      if (name === 'agents') {
        try {
          const res = await fetch(API + '/health');
          const data = await res.json();
          document.getElementById('agents-status').textContent = JSON.stringify(data.agents_loaded || [], null, 2);
        } catch (e) {
          document.getElementById('agents-status').textContent = 'Failed to load: ' + e.message;
        }
      }
      if (name === 'plugins') {
        try {
          const res = await fetch(API + '/health');
          const data = await res.json();
          document.getElementById('plugins-status').textContent = JSON.stringify(data.plugins_loaded || [], null, 2);
        } catch (e) {
          document.getElementById('plugins-status').textContent = 'Failed to load: ' + e.message;
        }
      }
      if (name === 'capabilities') {
        try {
          const res = await fetch(API + '/capabilities');
          const data = await res.json();
          document.getElementById('capabilities-status').textContent = JSON.stringify(data.capabilities || [], null, 2);
        } catch (e) {
          document.getElementById('capabilities-status').textContent = 'Failed to load: ' + e.message;
        }
      }
    }

    function statusClass(value) {
      const v = String(value || '').toLowerCase();
      if (v === 'running' || v === 'healthy' || v === 'active') return 'ok';
      if (v === 'idle') return 'idle';
      if (v === 'stopped' || v === 'error') return 'bad';
      return 'idle';
    }

    function setDot(id, text) {
      const dot = document.getElementById(id);
      const label = document.getElementById(id.replace('dot-', 'label-'));
      if (!dot) return;
      dot.className = 'dot ' + statusClass(text);
      if (label) label.textContent = text || '--';
    }

    function setKpi(id, text) {
      const el = document.getElementById('kpi-' + id);
      if (!el) return;
      el.textContent = text ?? '--';
      const cls = statusClass(text);
      el.className = 'kpi-value ' + (typeof text === 'number' ? 'count' : cls);
      const dot = document.getElementById('kpi-' + id + '-dot');
      if (dot) dot.className = 'dot ' + cls;
    }

    async function loadHealth() {
      const start = performance.now();
      try {
        const res = await fetch(API + '/status');
        const data = await res.json();
        const latency = Math.round(performance.now() - start);

        setKpi('kernel', data.kernel || '--');
        setKpi('knowledge', data.knowledge || '--');
        setKpi('simulation', data.simulation || '--');
        setKpi('reasoning', data.reasoning || '--');
        setKpi('hardware', data.hardware || '--');
        setKpi('devices', data.devices ?? 0);
        setKpi('agents', data.agents ?? 0);
        setKpi('plugins', data.plugins ?? 0);
        setKpi('capabilities', data.capabilities ?? 0);
        setKpi('facts', data.knowledge_facts ?? 0);

        setDot('dot-kernel', data.kernel);
        setDot('dot-knowledge', data.knowledge);
        setDot('dot-simulation', data.simulation);
        setDot('dot-reasoning', data.reasoning);
        setDot('dot-hardware', data.hardware);

        document.getElementById('bar-kernel').textContent = data.kernel || '--';
        document.getElementById('bar-devices').textContent = data.devices ?? 0;
        document.getElementById('bar-agents').textContent = data.agents ?? 0;
        document.getElementById('bar-knowledge').textContent = data.knowledge_facts ?? 0;
        document.getElementById('bar-latency').textContent = latency + 'ms';
        document.getElementById('overview-time').textContent = new Date().toLocaleTimeString();
      } catch (e) {
        console.error('Status fetch failed', e);
      }
    }

    let knownNodes = [];
    let knownEdges = [];

    function drawKnowledgeGraph() {
      const container = document.getElementById('knowledge-graph');
      if (!container) return;
      container.innerHTML = '';
      const w = container.clientWidth;
      const h = container.clientHeight;
      const nodes = Array.from({length: 12}, () => ({
        x: Math.random() * (w - 40) + 20,
        y: Math.random() * (h - 40) + 20,
      }));
      const edges = [];
      for (let i = 0; i < nodes.length - 1; i++) {
        if (Math.random() > 0.35) edges.push([i, i + 1]);
      }
      edges.forEach(([a, b]) => {
        const line = document.createElement('div');
        line.className = 'graph-edge';
        const dx = nodes[b].x - nodes[a].x;
        const dy = nodes[b].y - nodes[a].y;
        const len = Math.sqrt(dx * dx + dy * dy);
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        line.style.left = nodes[a].x + 'px';
        line.style.top = nodes[a].y + 'px';
        line.style.width = len + 'px';
        line.style.transform = 'rotate(' + angle + 'deg)';
        container.appendChild(line);
      });
      nodes.forEach(n => {
        const dot = document.createElement('div');
        dot.className = 'graph-node';
        dot.style.left = n.x + 'px';
        dot.style.top = n.y + 'px';
        container.appendChild(dot);
      });
    }

    function startEventStream() {
      if (eventSource) return;
      const list = document.getElementById('activity-list');
      list.innerHTML = '';
      eventSource = new EventSource(API + '/events');
      eventSource.onmessage = (ev) => {
        const item = document.createElement('div');
        item.className = 'activity-item fade-in';
        const data = JSON.parse(ev.data);
        const time = new Date(data.timestamp).toLocaleTimeString();
        const detail = Object.entries(data.data || {}).map(([k, v]) => k + '=' + JSON.stringify(v)).join(' ');
        item.innerHTML = '<div><span class="activity-type">' + escape(data.type) + '</span><span class="activity-detail">' + escape(detail || '') + '</span></div><span class="activity-time">' + escape(time) + '</span>';
        list.insertBefore(item, list.firstChild);
        if (list.children.length > 200) list.removeChild(list.lastChild);
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

    function init() {
      loadHealth();
      setInterval(loadHealth, 3000);
      setInterval(() => {
        const el = document.getElementById('uptime');
        if (!el) return;
        const t = Math.floor((Date.now() - sessionStart) / 1000);
        const m = Math.floor(t / 60);
        const s = t % 60;
        el.textContent = 'Uptime: ' + (m > 0 ? m + 'm ' : '') + s + 's';
      }, 1000);
      setInterval(() => {
        if (document.getElementById('page-knowledge').classList.contains('active')) drawKnowledgeGraph();
      }, 5000);
      const observer = new MutationObserver(() => {
        if (document.getElementById('page-knowledge').classList.contains('active')) drawKnowledgeGraph();
      });
      observer.observe(document.getElementById('page-knowledge'), { attributes: true, attributeFilter: ['class'] });
    }

    const sessionStart = Date.now();
    bootOverlay();
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
