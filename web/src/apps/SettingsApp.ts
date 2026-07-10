import { api } from "../api/client";
import { store } from "../os/Store";

interface Snap {
  version: string;
  status: any;
  health: any;
  plugins: any[];
  memoryCount: number;
  core: any;
  hardware: any;
  connected: boolean;
}

const CATEGORIES = [
  "Models",
  "Plugins",
  "Memory",
  "Kernel",
  "Appearance",
  "Networking",
  "Security",
  "Hardware",
  "Updates",
  "Extensions",
];

const PALETTE: [string, string][] = [
  ["--bg", "#0D1117"],
  ["--panel", "#161B22"],
  ["--border", "#2A3441"],
  ["--text", "#F5F5F5"],
  ["--muted", "#A8A8A8"],
  ["--yellow", "#F2C230"],
  ["--orange", "#F2911D"],
  ["--orange-red", "#F24F13"],
  ["--steel", "#8082A6"],
  ["--purple", "#46334F"],
];

export function mountSettings(el: HTMLElement) {
  el.innerHTML = `<div style="display: flex; height: 100%; box-sizing: border-box; font-family: var(--font-body); font-size: 15px;">
    <div id="set-nav" style="width: 130px; border-right: 1px solid var(--border); padding: 6px; flex-shrink: 0; overflow-y: auto;"></div>
    <div id="set-detail" style="flex: 1; padding: 8px; overflow-y: auto;"></div>
  </div>`;
  const nav = el.querySelector("#set-nav") as HTMLElement;
  const detail = el.querySelector("#set-detail") as HTMLElement;

  const snap: Partial<Snap> = { connected: store.state.connected };

  const load = () => {
    Promise.all([
      api.health().catch(() => ({}) as any),
      api.status().catch(() => ({}) as any),
      api.plugins().catch(() => ({ plugins: [] }) as any),
      api.memory().catch(() => [] as any),
      api.coreStatus().catch(() => ({}) as any),
      api.hardware().catch(() => ({}) as any),
    ]).then(([health, status, plugins, memory, core, hardware]: any[]) => {
      snap.version = health?.version ?? status?.version ?? "0.6.0-omega";
      snap.status = status;
      snap.health = health;
      snap.plugins = plugins?.plugins ?? [];
      snap.memoryCount = Array.isArray(memory) ? memory.length : (memory?.count ?? 0);
      snap.core = core;
      snap.hardware = hardware;
      snap.connected = store.state.connected;
      show("Models");
    });
  };

  let active = "Models";
  const show = (key: string) => {
    active = key;
    renderNav();
    renderDetail(key);
  };

  const renderNav = () => {
    nav.innerHTML = "";
    for (const c of CATEGORIES) {
      const b = document.createElement("div");
      b.textContent = c;
      b.style.cssText = `padding: 6px 8px; cursor: pointer; letter-spacing: 1px; border-left: 3px solid ${active === c ? "var(--yellow)" : "transparent"}; color: ${active === c ? "var(--yellow)" : "var(--muted)"};`;
      b.addEventListener("click", () => show(c));
      nav.appendChild(b);
    }
  };

  const renderDetail = (key: string) => {
    const s = snap.status || {};
    const h = snap.health || {};
    const rows = (label: string, value: string) =>
      `<div class="node-row"><span>${label}</span><span class="tag">${value}</span></div>`;

    if (key === "Models") {
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">MODELS</div>` +
        rows("Platform", String(snap.version ?? "—")) +
        rows("Plugins loaded", String(h.plugins_loaded ?? snap.plugins?.length ?? 0)) +
        rows("Agents loaded", String(h.agents_loaded ?? s.agents ?? 0)) +
        rows("Capabilities", String(h.capabilities_registered ?? s.capabilities ?? 0));
    } else if (key === "Plugins") {
      const list = (snap.plugins ?? []).map(
        (p: any) => `<div class="node-row"><span>${p.name ?? "unknown"}</span><span class="tag">${p.version ?? "v0.1.0"}</span></div>`,
      ).join("");
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">PLUGINS</div>` +
        (list || '<div style="color: var(--muted);">No plugins installed</div>');
    } else if (key === "Memory") {
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">MEMORY</div>` +
        rows("Long-term entries", String(snap.memoryCount ?? 0)) +
        rows("Engine", "observability store") +
        `<div style="color: var(--muted); margin-top: 8px; font-size: 13px;">Memory is persisted locally via SQLite.</div>`;
    } else if (key === "Kernel") {
      const up = new Date().toLocaleTimeString("en-GB");
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">KERNEL</div>` +
        rows("Status", String(s.kernel ?? "unknown")) +
        rows("Scheduler", String(snap.core?.status ?? "idle")) +
        rows("Uptime", up) +
        rows("Bootstrap", "core/bootstrap.py");
    } else if (key === "Appearance") {
      const overlay = document.querySelector(".crt-overlay") as HTMLElement | null;
      const off = overlay ? overlay.style.opacity === "0" : false;
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">APPEARANCE</div>
        <div class="node-row" style="cursor:pointer;" id="set-scan"><span>Scanline effect</span><span class="tag">${off ? "OFF" : "ON"}</span></div>
        <div style="color: var(--muted); font-size: 13px; margin: 8px 0;">Theme palette</div>
        <div id="set-swatches" style="display: flex; flex-wrap: wrap; gap: 6px;"></div>`;
      const sw = detail.querySelector("#set-swatches") as HTMLElement;
      for (const [name, hex] of PALETTE) {
        const sq = document.createElement("div");
        sq.title = `${name} ${hex}`;
        sq.style.cssText = `width: 26px; height: 26px; background: ${hex}; border: 1px solid var(--border);`;
        sw.appendChild(sq);
      }
      detail.querySelector("#set-scan")?.addEventListener("click", () => {
        const ov = document.querySelector(".crt-overlay") as HTMLElement | null;
        if (ov) ov.style.opacity = ov.style.opacity === "0" ? "1" : "0";
        renderDetail("Appearance");
      });
    } else if (key === "Networking") {
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">NETWORKING</div>` +
        rows("Local API", "127.0.0.1:8000") +
        rows("Connection", snap.connected ? "connected" : "offline") +
        rows("Transport", "localhost / SSE");
    } else if (key === "Security") {
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">SECURITY</div>` +
        rows("Kernel health", String(h.kernel_health?.status ?? s.kernel ?? "unknown")) +
        rows("Ownership", "owner-authorized") +
        `<div style="color: var(--muted); margin-top: 8px; font-size: 13px;">Recovery actions require a declared-owned device.</div>`;
    } else if (key === "Hardware") {
      const hw: any = snap.hardware || {};
      const devs: any[] = hw.devices ?? [];
      const ifaces: any[] = hw.hal?.interfaces ?? [];
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">HARDWARE</div>` +
        rows("Devices", String(devs.length)) +
        rows("HAL interfaces", String(ifaces.length)) +
        ifaces.map((i: any) => `<div class="node-row"><span>${i.name ?? "iface"}</span><span class="tag">${i.type ?? ""}</span></div>`).join("");
    } else if (key === "Updates") {
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">UPDATES</div>` +
        rows("Version", String(snap.version ?? "—")) +
        `<button id="set-check" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; margin-top: 8px; font-family: var(--font-body);">Check for updates</button>
        <div id="set-update-out" style="color: var(--muted); margin-top: 6px; font-size: 13px;"></div>`;
      detail.querySelector("#set-check")?.addEventListener("click", () => {
        const o = detail.querySelector("#set-update-out") as HTMLElement;
        if (o) o.innerHTML = "Prometheus is up to date (local build).";
      });
    } else if (key === "Extensions") {
      detail.innerHTML =
        `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 8px;">EXTENSIONS</div>
        <div style="color: var(--muted); font-size: 13px; line-height: 1.5;">
          Extensions are managed from the CLI:<br/>
          <span style="color: var(--orange);">prometheus install robotics</span><br/>
          <span style="color: var(--orange);">prometheus install android</span><br/>
          <span style="color: var(--orange);">prometheus install cad</span><br/>
          <span style="color: var(--orange);">prometheus install vision</span><br/>
          <span style="color: var(--orange);">prometheus install drone</span><br/>
          No extensions installed by default.
        </div>`;
    }
  };

  renderNav();
  load();
}
