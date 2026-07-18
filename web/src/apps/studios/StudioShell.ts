export interface StudioShellOptions {
  studioId: string;
  title: string;
  icon: string;
}

export interface StudioModuleContract {
  loadModule(name: string, params?: Record<string, unknown>): Promise<unknown>;
  saveState(): Promise<StudioState>;
  exportData(): Promise<Record<string, unknown>>;
  importData(data: Record<string, unknown>): Promise<void>;
  sendMessage(targetStudioId: string, action: string, payload: Record<string, unknown>): Promise<unknown>;
  onMessage(handler: (contract: CrossStudioContract) => Promise<unknown>): void;
}

export interface StudioState {
  studioId: string;
  data: Record<string, unknown>;
  dirty: boolean;
  updatedAt: number;
}

export interface CrossStudioContract {
  studioId: string;
  action: string;
  payload: Record<string, unknown>;
  response?: Record<string, unknown>;
}

const DEFAULT_SIDEBAR_TOOLS = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "modules", label: "Modules", icon: "🧩" },
  { id: "files", label: "Files", icon: "📁" },
  { id: "logs", label: "Logs", icon: "📋" },
  { id: "settings", label: "Settings", icon: "⚙️" },
];

export class StudioShell {
  private container: HTMLElement;
  private options: StudioShellOptions;
  private tools: { id: string; label: string; icon: string }[];
  private activeTool: string;
  private state: StudioState;
  private messageHandlers: Map<string, (contract: CrossStudioContract) => Promise<unknown>>;
  private statusInterval: number | null;

  constructor(container: HTMLElement, options: StudioShellOptions, tools?: { id: string; label: string; icon: string }[]) {
    this.container = container;
    this.options = options;
    this.tools = tools ?? DEFAULT_SIDEBAR_TOOLS;
    this.activeTool = this.tools[0]?.id ?? "dashboard";
    this.state = {
      studioId: options.studioId,
      data: {},
      dirty: false,
      updatedAt: Date.now(),
    };
    this.messageHandlers = new Map();
    this.statusInterval = null;
    this.render();
    this.startStatusTick();
  }

  private render() {
    const toolsHtml = this.tools
      .map(
        (t) =>
          `<div class="studio-tool" data-tool="${t.id}" style="padding: 8px 12px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 13px; color: ${this.activeTool === t.id ? "var(--yellow)" : "var(--muted)"};">
            <span>${t.icon}</span><span>${t.label}</span>
          </div>`,
      )
      .join("");

    this.container.innerHTML = `<div style="display: flex; flex-direction: column; height: 100%; box-sizing: border-box; font-family: var(--font-body);">
      <div style="display: flex; flex: 1; min-height: 0;">
        <div style="width: 200px; background: var(--bg); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0;">
          <div style="padding: 12px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 18px;">${this.options.icon}</span>
            <div>
              <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">${this.options.title.toUpperCase()}</div>
              <div style="font-size: 11px; color: var(--muted);">Studio Shell</div>
            </div>
          </div>
          <div style="flex: 1; overflow-y: auto; padding: 4px 0;">${toolsHtml}</div>
          <div id="studio-status" style="padding: 8px 12px; border-top: 1px solid var(--border); font-size: 11px; color: var(--muted);">
            status: ready
          </div>
        </div>
        <div id="studio-main" style="flex: 1; overflow-y: auto; padding: 12px; background: var(--bg);"></div>
      </div>
      <div id="studio-statusbar" style="height: 24px; background: var(--border); display: flex; align-items: center; padding: 0 12px; font-size: 11px; color: var(--muted); gap: 16px;">
        <span>Studio: ${this.options.studioId}</span>
        <span id="studio-dirty">Clean</span>
        <span id="studio-time"></span>
      </div>
    </div>`;

    const toolEls = this.container.querySelectorAll(".studio-tool");
    toolEls.forEach((el) => {
      el.addEventListener("click", () => {
        const toolId = (el as HTMLElement).dataset.tool;
        if (toolId) this.setActiveTool(toolId);
      });
    });

    this.updateTimestamp();
  }

  private startStatusTick() {
    if (this.statusInterval !== null) return;
    this.statusInterval = window.setInterval(() => {
      this.updateTimestamp();
    }, 1000);
  }

  private updateTimestamp() {
    const timeEl = this.container.querySelector("#studio-time");
    if (timeEl) {
      timeEl.textContent = new Date().toLocaleTimeString();
    }
    const dirtyEl = this.container.querySelector("#studio-dirty");
    if (dirtyEl) {
      dirtyEl.textContent = this.state.dirty ? "Unsaved changes" : "Clean";
      (dirtyEl as HTMLElement).style.color = this.state.dirty ? "var(--orange-red)" : "var(--muted)";
    }
  }

  private setActiveTool(toolId: string) {
    this.activeTool = toolId;
    const toolEls = this.container.querySelectorAll(".studio-tool");
    toolEls.forEach((el) => {
      const id = (el as HTMLElement).dataset.tool;
      const isActive = id === toolId;
      (el as HTMLElement).style.color = isActive ? "var(--yellow)" : "var(--muted)";
    });
  }

  public loadModule(name: string, params?: Record<string, unknown>): Promise<unknown> {
    const main = this.container.querySelector("#studio-main") as HTMLElement;
    if (!main) return Promise.resolve(undefined);
    main.innerHTML = `<div style="color: var(--muted);">Loading module: ${name}...</div>`;
    return new Promise((resolve) => {
      setTimeout(() => {
        main.innerHTML = `<div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">MODULE: ${name.toUpperCase()}</div>
          <div style="color: var(--muted); font-size: 13px;">Module rendered with params: ${JSON.stringify(params ?? {})}</div>`;
        resolve(undefined);
      }, 100);
    });
  }

  public async saveState(): Promise<StudioState> {
    this.state.updatedAt = Date.now();
    this.state.dirty = false;
    this.updateTimestamp();
    return { ...this.state };
  }

  public async exportData(): Promise<Record<string, unknown>> {
    return {
      studioId: this.state.studioId,
      exportedAt: Date.now(),
      data: { ...this.state.data },
    };
  }

  public async importData(data: Record<string, unknown>): Promise<void> {
    if (data.data && typeof data.data === "object") {
      this.state.data = { ...(data.data as Record<string, unknown>) };
      this.state.dirty = true;
      this.state.updatedAt = Date.now();
      this.updateTimestamp();
    }
  }

  public sendMessage(targetStudioId: string, action: string, payload: Record<string, unknown>): Promise<unknown> {
    const contract: CrossStudioContract = {
      studioId: targetStudioId,
      action,
      payload,
    };
    const handler = this.messageHandlers.get(targetStudioId);
    if (handler) {
      return handler(contract);
    }
    return Promise.reject(new Error(`No handler registered for studio: ${targetStudioId}`));
  }

  public onMessage(handler: (contract: CrossStudioContract) => Promise<unknown>): void {
    this.messageHandlers.set(this.options.studioId, handler);
  }

  public setStatus(text: string) {
    const statusEl = this.container.querySelector("#studio-status");
    if (statusEl) {
      statusEl.textContent = `status: ${text}`;
    }
  }

  public destroy() {
    if (this.statusInterval !== null) {
      clearInterval(this.statusInterval);
      this.statusInterval = null;
    }
  }
}

export const CROSS_STUDIO_CONTRACT_VERSION = "1.0.0";
