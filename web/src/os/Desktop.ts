import { AppWindow } from "../apps/App";
import { WindowManager } from "./WindowManager";
import { DockItem } from "./Dock";
import { StatusBarState } from "./StatusBar";
import { store } from "./Store";
import { api } from "../api/client";
import { mountKernel, mountKnowledge, mountSimulation, mountReasoning, mountHardware, mountDevices, mountAgents, mountFiles, mountPlugins, mountMemory, mountActivity, mountSettings, mountAssistant } from "../apps";

const APPS: (Omit<AppWindow, "id"> & { key: string })[] = [
  { key: "kernel", title: "Kernel", icon: "[K]", mount: mountKernel },
  { key: "knowledge", title: "Knowledge", icon: "[G]", mount: mountKnowledge },
  { key: "simulation", title: "Simulation", icon: "[S]", mount: mountSimulation },
  { key: "reasoning", title: "Reasoning", icon: "[R]", mount: mountReasoning },
  { key: "hardware", title: "Hardware", icon: "[H]", mount: mountHardware },
  { key: "devices", title: "Devices", icon: "[D]", mount: mountDevices },
  { key: "agents", title: "Agents", icon: "[A]", mount: mountAgents },
  { key: "files", title: "Files", icon: "[F]", mount: mountFiles },
  { key: "plugins", title: "Plugins", icon: "[P]", mount: mountPlugins },
  { key: "memory", title: "Memory", icon: "[M]", mount: mountMemory },
  { key: "activity", title: "Activity", icon: "[L]", mount: mountActivity },
  { key: "settings", title: "Settings", icon: "[X]", mount: mountSettings },
  { key: "assistant", title: "Assistant", icon: "[/]", mount: mountAssistant },
];

export class Desktop {
  private el: HTMLElement;
  private wm: WindowManager;
  private openWindows: Set<string> = new Set();

  constructor(container: HTMLElement) {
    this.el = container;
    this.el.style.display = "flex";
    this.el.style.flexDirection = "column";
    this.el.style.height = "100vh";
    this.el.style.width = "100vw";
    this.el.style.overflow = "hidden";
    this.el.style.position = "relative";
    this.el.style.background = "var(--bg)";

    const topBar = document.createElement("div");
    topBar.className = "topbar";
    topBar.innerHTML = `
      <span style="color: var(--yellow);">PROMETHEUS</span>
      <span id="topbar-version" style="color: var(--muted);">v0.6.0-omega</span>
      <span id="topbar-time" style="color: var(--muted);"></span>
    `;
    this.el.appendChild(topBar);

    const center = document.createElement("div");
    center.style.flex = "1";
    center.style.position = "relative";
    center.style.overflow = "hidden";
    this.el.appendChild(center);

    this.wm = new WindowManager(center);

    const dock = document.createElement("div");
    dock.className = "dock";
    for (const app of APPS) {
      const btn = document.createElement("button");
      btn.className = "dock-item";
      btn.textContent = app.icon;
      btn.title = app.title;
      btn.addEventListener("click", () => this.launch(app));
      dock.appendChild(btn);
    }
    this.el.appendChild(dock);

    const term = document.createElement("div");
    term.className = "terminal scrollbar-thin";
    term.id = "terminal-root";
    term.style.height = "160px";
    term.style.flexShrink = "0";
    this.el.appendChild(term);

    const inputLine = document.createElement("div");
    inputLine.className = "terminal-input-line";
    inputLine.innerHTML = `<span>root@prometheus:~$</span>`;
    const input = document.createElement("input");
    input.className = "terminal-input";
    input.spellcheck = false;
    input.autocomplete = "off";
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const val = input.value.trim();
        if (val) {
          appendOutput(term, `root@prometheus:~$ ${val}`);
          handleCommand(val, this, term);
          input.value = "";
        }
      }
    });
    inputLine.appendChild(input);
    term.appendChild(inputLine);
    term.appendChild(Object.assign(document.createElement("hr"), { style: "border: none; border-top: 1px solid var(--border); margin: 4px 0;" }));
    term.insertBefore(document.createElement("div"), inputLine);

    setInterval(() => {
      document.getElementById("topbar-time")!.textContent = new Date().toLocaleTimeString();
    }, 1000);

    store.subscribe((s) => {
      const ver = document.getElementById("topbar-version");
      if (ver && s.status && typeof s.status === "object" && "version" in s.status) {
        ver.textContent = String((s.status as any).version);
      }
    });
  }

  launch(app: Omit<AppWindow, "id"> & { key: string }) {
    const id = app.key;
    this.wm.open(
      { title: app.title, icon: app.icon, content: document.createElement("div"), w: 520, h: 360, x: 100, y: 100, minimized: false, maximized: false, zIndex: 100 },
      app.key
    );
    const body = document.querySelector(`.window-body[data-win="${id}"]`) as HTMLElement;
    if (body && body.firstElementChild instanceof HTMLElement) {
      app.mount(body.firstElementChild);
    }
    this.openWindows.add(id);
  }

  getWindowManager(): WindowManager {
    return this.wm;
  }

  getElement(): HTMLElement {
    return this.el;
  }
}

function appendOutput(el: HTMLElement, text: string) {
  const line = document.createElement("div");
  line.style.marginBottom = "2px";
  line.textContent = text;
  el.insertBefore(line, el.lastElementChild);
  el.scrollTop = el.scrollHeight;
}

async function handleCommand(cmd: string, desktop: Desktop, term: HTMLElement) {
  const parts = cmd.split(" ");
  const c = parts[0].toLowerCase();
  const arg = parts.slice(1).join(" ");
  switch (c) {
    case "help":
      appendOutput(term, "Commands: help, status, devices, agents, kernel, open kernel|knowledge|simulation|reasoning|hardware|devices|agents|files|plugins|memory|activity|settings|assistant, clear");
      break;
    case "status": {
      const s = await api.status();
      appendOutput(term, JSON.stringify(s, null, 2));
      break;
    }
    case "devices": {
      const s = await api.status();
      appendOutput(term, JSON.stringify({ devices: (s as any).devices }, null, 2));
      break;
    }
    case "agents": {
      const s = await api.status();
      appendOutput(term, JSON.stringify({ agents: (s as any).agent_statuses ?? (s as any).agents }, null, 2));
      break;
    }
    case "kernel": {
      const s = await api.status();
      appendOutput(term, JSON.stringify({ kernel: (s as any).kernel }, null, 2));
      break;
    }
    case "open":
      if (arg) {
        const app = APPS.find(a => a.title.toLowerCase() === arg || a.key.toLowerCase() === arg);
        if (app) desktop.launch(app);
        else appendOutput(term, `Unknown app: ${arg}`);
      }
      break;
    case "clear":
      const lines = term.querySelectorAll("div");
      lines.forEach((l) => l.remove());
      break;
    default:
      appendOutput(term, `Command not found: ${c}`);
      break;
  }
}
