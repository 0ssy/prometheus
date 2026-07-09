import { WindowManager } from "./WindowManager";
import { store } from "./Store";
import { api } from "../api/client";
import { Terminal, TerminalContext } from "../terminal/Terminal";
import {
  mountKernel,
  mountKnowledge,
  mountSimulation,
  mountReasoning,
  mountHardware,
  mountDevices,
  mountAgents,
  mountFiles,
  mountPlugins,
  mountMemory,
  mountActivity,
  mountSettings,
  mountAssistant,
} from "../apps";

const BOOT_LOGO = `██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗
██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝
██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗
██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝
██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝`;

interface AppDef {
  key: string;
  title: string;
  mount: (el: HTMLElement) => void;
  w?: number;
  h?: number;
}

const APPS: Record<string, AppDef> = {
  kernel: { key: "kernel", title: "KERNEL", mount: mountKernel, w: 380, h: 260 },
  knowledge: { key: "knowledge", title: "KNOWLEDGE", mount: mountKnowledge, w: 420, h: 320 },
  simulation: { key: "simulation", title: "SIMULATION", mount: mountSimulation, w: 360, h: 300 },
  reasoning: { key: "reasoning", title: "REASONING", mount: mountReasoning, w: 360, h: 240 },
  hardware: { key: "hardware", title: "HARDWARE", mount: mountHardware, w: 360, h: 280 },
  devices: { key: "devices", title: "DEVICES", mount: mountDevices, w: 360, h: 280 },
  agents: { key: "agents", title: "AGENTS", mount: mountAgents, w: 340, h: 340 },
  files: { key: "files", title: "FILES", mount: mountFiles, w: 360, h: 300 },
  plugins: { key: "plugins", title: "PLUGINS", mount: mountPlugins, w: 360, h: 280 },
  memory: { key: "memory", title: "MEMORY", mount: mountMemory, w: 340, h: 260 },
  settings: { key: "settings", title: "SETTINGS", mount: mountSettings, w: 360, h: 280 },
  assistant: { key: "assistant", title: "ASSISTANT", mount: mountAssistant, w: 420, h: 340 },
  activity: { key: "activity", title: "ACTIVITY FEED", mount: mountActivity, w: 360, h: 320 },
};

const DOCK_KEYS = [
  "kernel",
  "knowledge",
  "simulation",
  "reasoning",
  "hardware",
  "devices",
  "agents",
  "files",
  "plugins",
  "memory",
  "settings",
  "assistant",
];

const DOCK_ICONS: Record<string, string> = {
  kernel: '<rect x="2" y="2" width="8" height="8" fill="currentColor"/>',
  knowledge: '<circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="6" r="1.2" fill="currentColor"/>',
  simulation: '<path d="M2 9 L4 5 L6 7 L10 2" stroke="currentColor" stroke-width="1.5" fill="none"/>',
  reasoning: '<path d="M6 1 L11 6 L6 11 L1 6 Z" fill="none" stroke="currentColor" stroke-width="1.5"/>',
  hardware: '<rect x="2" y="3" width="8" height="6" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="4.5" y="9" width="3" height="2" fill="currentColor"/>',
  devices: '<rect x="3" y="1" width="6" height="10" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="9" r="0.8" fill="currentColor"/>',
  agents: '<circle cx="6" cy="4" r="2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 11 Q6 7 10 11" fill="none" stroke="currentColor" stroke-width="1.5"/>',
  files: '<path d="M2 2 H7 L9 4 V10 H2 Z" fill="none" stroke="currentColor" stroke-width="1.5"/>',
  plugins: '<rect x="2" y="4" width="8" height="6" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="4.5" y="1.5" width="1.5" height="3" fill="currentColor"/><rect x="7" y="1.5" width="1.5" height="3" fill="currentColor"/>',
  memory: '<rect x="1.5" y="3" width="9" height="6" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="1.5" y1="6" x2="10.5" y2="6" stroke="currentColor" stroke-width="1"/>',
  settings: '<circle cx="6" cy="6" r="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 1 V2.5 M6 9.5 V11 M1 6 H2.5 M9.5 6 H11 M2.6 2.6 L3.6 3.6 M8.4 8.4 L9.4 9.4 M2.6 9.4 L3.6 8.4 M8.4 3.6 L9.4 2.6" stroke="currentColor" stroke-width="1"/>',
  assistant: '<circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="4.3" cy="5.5" r="0.8" fill="currentColor"/><circle cx="7.7" cy="5.5" r="0.8" fill="currentColor"/>',
};

export class Desktop {
  private el: HTMLElement;
  private wm: WindowManager;
  private activityFeed: HTMLElement;
  private dockButtons: Map<string, HTMLButtonElement> = new Map();
  private offset = 0;
  private terminalCtx: TerminalContext;

  constructor(container: HTMLElement) {
    this.el = container;
    this.el.id = "os-root";
    this.el.style.position = "relative";
    this.el.style.width = "100%";
    this.el.style.height = "100vh";
    this.el.style.background = "var(--bg)";
    this.el.style.overflow = "hidden";

    const topbar = document.createElement("div");
    topbar.id = "topbar";
    topbar.innerHTML = `
      <pre class="brand-ascii">${BOOT_LOGO}</pre>
      <div class="status-group">
        <span><span class="dot"></span>connected</span>
        <span><span class="dot"></span>all systems operational</span>
        <span id="clock">00:00:00</span>
      </div>`;
    this.el.appendChild(topbar);

    const workspace = document.createElement("div");
    workspace.id = "workspace";
    workspace.innerHTML = `
      <div id="welcome">
        <h1>WELCOME BACK, JOSEPH.</h1>
        <p>Engineering Workspace Ready. All systems operational.</p>
        <p style="color:var(--yellow);">&gt; What would you like to build today?</p>
      </div>
      <div id="stat-grid"></div>
      <div id="dock-hint">Terminal is always available below. Try: <span>show devices</span>, <span>run simulation</span>, <span>help</span></div>`;
    this.el.appendChild(workspace);

    const dock = document.createElement("div");
    dock.id = "dock";
    this.el.appendChild(dock);

    const activityToggle = document.createElement("div");
    activityToggle.id = "activity-toggle";
    activityToggle.textContent = "ACTIVITY ▾";
    this.el.appendChild(activityToggle);

    this.activityFeed = document.createElement("div");
    this.activityFeed.id = "activity-feed";
    this.el.appendChild(this.activityFeed);

    const termbar = document.createElement("div");
    termbar.id = "termbar";
    this.el.appendChild(termbar);

    this.wm = new WindowManager(workspace);

    this.terminalCtx = {
      openApp: (id) => this.openApp(id),
      logActivity: (text) => this.logActivity(text),
    };

    this.buildDock(dock);

    new Terminal(termbar, this.terminalCtx);

    this.initStore();
    this.startClock();

    activityToggle.addEventListener("click", () => {
      const open = this.activityFeed.style.display === "block";
      this.activityFeed.style.display = open ? "none" : "block";
      activityToggle.classList.toggle("active", !open);
    });
  }

  private buildDock(dock: HTMLElement) {
    for (const key of DOCK_KEYS) {
      const btn = document.createElement("button");
      btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 12 12" style="vertical-align:-2px;margin-right:5px;">${DOCK_ICONS[key]}</svg>${key.toUpperCase()}`;
      btn.addEventListener("click", () => this.openApp(key));
      dock.appendChild(btn);
      this.dockButtons.set(key, btn);
    }
  }

  private initStore() {
    store.loadStatus();
    store.startSSE();
    this.renderStatGrid(store.state.status);
    store.subscribe((s) => {
      this.renderStatGrid(s.status);
      this.renderActivity(s.events);
    });
  }

  private startClock() {
    const clock = this.el.querySelector("#clock");
    if (clock) clock.textContent = new Date().toLocaleTimeString("en-GB");
    setInterval(() => {
      const c = this.el.querySelector("#clock");
      if (c) c.textContent = new Date().toLocaleTimeString("en-GB");
    }, 1000);
  }

  openApp(key: string) {
    const app = APPS[key];
    if (!app) {
      return;
    }
    const btn = this.dockButtons.get(key);
    const content = document.createElement("div");
    content.style.height = "100%";
    const id = this.wm.open(
      key,
      {
        title: app.title,
        content,
        w: app.w || 360,
        h: app.h || 280,
        x: 60 + (this.offset % 5) * 40,
        y: 20 + (this.offset % 5) * 30,
      },
      (el) => app.mount(el),
    );
    this.offset++;
    btn?.classList.add("active");
    const handle = (this.wm as any).windows.get(id) as { onClose?: () => void } | undefined;
    if (handle) handle.onClose = () => btn?.classList.remove("active");
  }

  logActivity(text: string) {
    store.pushEvent({ type: "activity", timestamp: new Date().toISOString(), data: { message: text } });
  }

  private renderStatGrid(status: Record<string, unknown> | null) {
    const grid = this.el.querySelector("#stat-grid");
    if (!grid) return;
    const s = (status || {}) as any;
    const panels = [
      { label: "Kernel", value: s.kernel === "Running" ? "ONLINE" : s.kernel || "--" },
      { label: "Knowledge", value: `${s.knowledge_facts ?? 0} facts` },
      { label: "Simulation", value: s.simulation || "IDLE" },
      { label: "Reasoning", value: s.reasoning || "READY" },
      { label: "Hardware", value: s.hardware || "IDLE" },
      { label: "Agents", value: `${s.agents ?? 0} active` },
      { label: "Plugins", value: `${s.plugins ?? 0} loaded` },
      { label: "Connected Devices", value: String(s.devices ?? 0) },
      { label: "Knowledge Facts", value: String(s.knowledge_facts ?? 0) },
      { label: "Capabilities", value: String(s.capabilities ?? 0) },
    ];
    grid.innerHTML = "";
    for (const p of panels) {
      const div = document.createElement("div");
      div.className = "stat-panel";
      div.innerHTML = `<div class="label">${p.label}</div><div class="value">${p.value}</div>
        <div class="pulse-bar"><div class="pulse-fill" style="animation-delay:${Math.random() * 2}s"></div></div>`;
      grid.appendChild(div);
    }
  }

  private renderActivity(events: any[]) {
    this.activityFeed.innerHTML = "";
    for (const e of (events || []).slice(0, 60)) {
      const entry = document.createElement("div");
      entry.className = "entry";
      const t = new Date(e.timestamp).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
      const msg = e.data && e.data.message ? e.data.message : e.type;
      entry.innerHTML = `<span class="t">${t}</span>${msg}`;
      this.activityFeed.appendChild(entry);
    }
  }
}
