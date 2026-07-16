import { WindowManager } from "./WindowManager";
import { store } from "./Store";
import { api } from "../api/client";
import { Terminal, TerminalContext } from "../terminal/Terminal";
import { showOnboarding } from "./Onboarding";
import {
  mountKnowledge,
  mountSimulation,
  mountReasoning,
  mountHardware,
  mountDevices,
  mountAgents,
  mountFiles,
  mountPlugins,
  mountMemory,
  mountSettings,
  mountAssistant,
  mountMonitor,
  mountJobs,
  mountWorkflow,
  mountEngineeringStudio,
  mountStatus,
  mountGovernance,
  mountOS,
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
  monitor: { key: "monitor", title: "MONITOR", mount: mountMonitor, w: 420, h: 360 },
  jobs: { key: "jobs", title: "JOBS", mount: mountJobs, w: 400, h: 320 },
  workflow: { key: "workflow", title: "WORKFLOWS", mount: mountWorkflow, w: 420, h: 360 },
  engineering: { key: "engineering", title: "ENGINEERING", mount: mountEngineeringStudio, w: 420, h: 360 },
  status: { key: "status", title: "STATUS", mount: mountStatus, w: 420, h: 320 },
  governance: { key: "governance", title: "GOVERNANCE", mount: mountGovernance, w: 420, h: 360 },
  os: { key: "os", title: "PROMETHEUS OS", mount: mountOS, w: 460, h: 400 },
};

const DOCK_KEYS = [
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
  "monitor",
  "jobs",
  "workflow",
  "engineering",
  "status",
  "governance",
  "os",
];

const DOCK_ICONS: Record<string, string> = {
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
  monitor: '<rect x="2" y="2" width="8" height="6" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3.5" y="3.5" width="5" height="3" fill="currentColor"/><path d="M2 9 L6 7 L10 9" stroke="currentColor" stroke-width="1.2" fill="none"/>',
  jobs: '<rect x="2" y="2" width="8" height="8" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4 5 L6 7 L9 4" stroke="currentColor" stroke-width="1.2" fill="none"/>',
  workflow: '<circle cx="3" cy="6" r="1.5" fill="currentColor"/><circle cx="9" cy="6" r="1.5" fill="currentColor"/><path d="M4.5 6 L7.5 6 M4.5 6 L3 3 M7.5 6 L10 3 M4.5 6 L3 9 M7.5 6 L10 9" stroke="currentColor" stroke-width="1"/>',
  engineering: '<path d="M2 10 L6 2 L10 10" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4 10 L6 6 L8 10" fill="none" stroke="currentColor" stroke-width="1.5"/>',
  status: '<rect x="2" y="3" width="8" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="6" r="1.6" fill="currentColor"/>',
  governance: '<rect x="2" y="2" width="8" height="8" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4 6 L5.5 7.5 L8 4.5" stroke="currentColor" stroke-width="1.2" fill="none"/>',
  os: '<rect x="1.5" y="2" width="9" height="8" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="6" cy="6" r="1.6" fill="currentColor"/><path d="M3 9 H9" stroke="currentColor" stroke-width="1"/>',
};

export class Desktop {
  private el: HTMLElement;
  private wm: WindowManager;
  private activityFeed: HTMLElement;
  private dockButtons: Map<string, HTMLButtonElement> = new Map();
  private offset = 0;
  private terminalCtx: TerminalContext;
  private terminal!: Terminal;

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

    this.terminal = new Terminal(termbar, this.terminalCtx);

    this.setupInteractions();

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
    store.subscribe((s) => {
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

  openApp(key: string, silent = false) {
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
    if (!silent) this.terminal?.logGui("> open " + app.title);
    const handle = (this.wm as any).windows.get(id) as { onClose?: () => void } | undefined;
    if (handle) handle.onClose = () => btn?.classList.remove("active");
  }

  private setupInteractions() {
    this.wm.onChange((wins) => {
      try {
        localStorage.setItem("prometheus_session_v1", JSON.stringify(wins));
      } catch {}
    });
    document.addEventListener("keydown", (e) => this.onKey(e));
    this.addHelpButton();
    this.restoreSession();
    showOnboarding(this.el);
  }

  private restoreSession() {
    try {
      const raw = localStorage.getItem("prometheus_session_v1");
      if (!raw) return;
      const wins: { id: string; minimized?: boolean; maximized?: boolean }[] = JSON.parse(raw);
      for (const w of wins) {
        if (!APPS[w.id]) continue;
        this.openApp(w.id, true);
        if (w.minimized) this.wm.minimize(w.id);
        else if (w.maximized) this.wm.toggleMaximize(w.id);
      }
    } catch {}
  }

  private onKey(e: KeyboardEvent) {
    const target = e.target as HTMLElement | null;
    const typing =
      !!target &&
      (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
    const mod = e.ctrlKey || e.metaKey;

    if (mod) {
      const k = e.key.toLowerCase();
      if (k === ",") {
        e.preventDefault();
        this.openApp("settings", true);
      } else if (k === "/") {
        e.preventDefault();
        this.toggleShortcuts();
      } else if (k === "w") {
        e.preventDefault();
        this.wm.closeTop();
      } else if (k === "m") {
        e.preventDefault();
        this.wm.minimizeTop();
      }
      return;
    }

    if (e.key === "Escape") {
      this.wm.closeTop();
      return;
    }
    if (e.key === "F11") {
      e.preventDefault();
      this.wm.maximizeTop();
      return;
    }

    if (typing) return;

    if (e.key === "`" || e.key === "~") {
      this.focusTerminal();
      return;
    }
    if (/^[1-9]$/.test(e.key)) {
      const idx = parseInt(e.key, 10) - 1;
      if (DOCK_KEYS[idx]) this.openApp(DOCK_KEYS[idx], true);
      return;
    }
    if (e.key === "0" && DOCK_KEYS[9]) {
      this.openApp(DOCK_KEYS[9], true);
    }
  }

  private focusTerminal() {
    const inp = document.getElementById("terminput") as HTMLInputElement | null;
    inp?.focus();
  }

  private addHelpButton() {
    const group = this.el.querySelector("#topbar .status-group");
    if (!group) return;
    const help = document.createElement("span");
    help.id = "help-btn";
    help.textContent = "?";
    help.title = "Keyboard shortcuts & help";
    help.addEventListener("click", () => this.toggleShortcuts());
    group.appendChild(help);
  }

  private toggleShortcuts() {
    const existing = document.getElementById("shortcuts");
    if (existing) {
      existing.remove();
      return;
    }
    const el = document.createElement("div");
    el.id = "shortcuts";
    el.innerHTML = `
      <div class="ob-card">
        <div class="ob-title">KEYBOARD SHORTCUTS</div>
        <div class="ob-rows">
          <div class="ob-row"><span>Open dock app</span><span class="ob-key">1&ndash;9 , 0</span></div>
          <div class="ob-row"><span>Focus terminal</span><span class="ob-key">\`</span></div>
          <div class="ob-row"><span>Close focused window</span><span class="ob-key">Esc / Ctrl+W</span></div>
          <div class="ob-row"><span>Minimize focused window</span><span class="ob-key">Ctrl+M</span></div>
          <div class="ob-row"><span>Maximize focused window</span><span class="ob-key">F11</span></div>
          <div class="ob-row"><span>Open Settings</span><span class="ob-key">Ctrl+,</span></div>
          <div class="ob-row"><span>Toggle this help</span><span class="ob-key">Ctrl+/</span></div>
        </div>
        <button class="ob-btn" id="shortcuts-close">GOT IT</button>
      </div>`;
    this.el.appendChild(el);
    el.querySelector("#shortcuts-close")?.addEventListener("click", () => el.remove());
  }

  logActivity(text: string) {
    store.pushEvent({ type: "activity", timestamp: new Date().toISOString(), data: { message: text } });
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
