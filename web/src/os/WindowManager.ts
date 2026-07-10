export interface WindowHandle {
  title: string;
  icon?: string;
  x: number;
  y: number;
  w: number;
  h: number;
  zIndex?: number;
  content: HTMLElement;
  onClose?: () => void;
}

interface ManagedWindow {
  id: string;
  handle: WindowHandle;
  minimized: boolean;
  maximized: boolean;
  prev: { x: number; y: number; w: number; h: number } | null;
}

export interface SessionWindow {
  id: string;
  title: string;
  minimized: boolean;
  maximized: boolean;
}

export class WindowManager {
  private windows: Map<string, ManagedWindow> = new Map();
  private nextZ = 100;
  private container: HTMLElement;
  private taskbar: HTMLElement;
  private dragState: { id: string; startX: number; startY: number; origX: number; origY: number } | null = null;
  private resizeState: { id: string; startX: number; startY: number; origW: number; origH: number } | null = null;
  private changeListener?: (wins: SessionWindow[]) => void;

  constructor(container: HTMLElement) {
    this.container = container;
    this.container.addEventListener("mousemove", (e) => this.onMouseMove(e));
    this.container.addEventListener("mouseup", () => this.onMouseUp());

    this.taskbar = document.createElement("div");
    this.taskbar.id = "taskbar";
    this.container.appendChild(this.taskbar);
  }

  open(id: string, handle: WindowHandle, onMount?: (el: HTMLElement) => void): string {
    const existing = this.windows.get(id);
    if (existing) {
      if (existing.minimized) this.restore(id);
      else this.focus(id);
      return id;
    }

    let { x, y, w, h } = handle;
    const saved = localStorage.getItem(`prometheus_window_${id}`);
    if (saved) {
      try {
        const pos = JSON.parse(saved);
        x = pos.x ?? x;
        y = pos.y ?? y;
        w = pos.w ?? w;
        h = pos.h ?? h;
      } catch {}
    }

    const win: WindowHandle = { ...handle, x, y, w, h, zIndex: ++this.nextZ };
    this.windows.set(id, {
      id,
      handle: win,
      minimized: false,
      maximized: false,
      prev: null,
    });
    this.render(id, win, onMount);
    this.renderTaskbar();
    this.emitChange();
    return id;
  }

  onChange(fn: (wins: SessionWindow[]) => void) {
    this.changeListener = fn;
  }

  private snapshot(): SessionWindow[] {
    return [...this.windows.values()].map((w) => ({
      id: w.id,
      title: w.handle.title,
      minimized: w.minimized,
      maximized: w.maximized,
    }));
  }

  private emitChange() {
    this.changeListener?.(this.snapshot());
  }

  focusedId(): string | null {
    let topId: string | null = null;
    let topZ = -1;
    for (const [id, w] of this.windows) {
      if (!w.minimized && (w.handle.zIndex ?? 0) > topZ) {
        topZ = w.handle.zIndex ?? 0;
        topId = id;
      }
    }
    return topId;
  }

  closeTop() {
    const id = this.focusedId();
    if (id) this.close(id);
  }

  minimizeTop() {
    const id = this.focusedId();
    if (id) this.minimize(id);
  }

  maximizeTop() {
    const id = this.focusedId();
    if (id) this.toggleMaximize(id);
  }

  close(id: string) {
    const win = this.windows.get(id);
    if (win) {
      const el = document.getElementById(`win-${id}`);
      el?.remove();
      this.windows.delete(id);
      win.handle.onClose?.();
      this.renderTaskbar();
      this.emitChange();
    }
  }

  focus(id: string) {
    const win = this.windows.get(id);
    if (win) {
      win.handle.zIndex = ++this.nextZ;
      const el = document.getElementById(`win-${id}`);
      if (el) el.style.zIndex = String(win.handle.zIndex);
    }
  }

  isOpen(id: string): boolean {
    return this.windows.has(id);
  }

  minimize(id: string) {
    const win = this.windows.get(id);
    if (!win) return;
    const el = document.getElementById(`win-${id}`);
    if (el) el.style.display = "none";
    win.minimized = true;
    this.renderTaskbar();
    this.emitChange();
  }

  restore(id: string) {
    const win = this.windows.get(id);
    if (!win) return;
    const el = document.getElementById(`win-${id}`);
    if (el) el.style.display = "flex";
    win.minimized = false;
    this.focus(id);
    this.renderTaskbar();
    this.emitChange();
  }

  toggleMaximize(id: string) {
    const win = this.windows.get(id);
    if (!win) return;
    const el = document.getElementById(`win-${id}`);
    if (!el) return;
    if (win.maximized && win.prev) {
      const p = win.prev;
      el.style.left = `${p.x}px`;
      el.style.top = `${p.y}px`;
      el.style.width = `${p.w}px`;
      el.style.height = `${p.h}px`;
      win.handle.x = p.x;
      win.handle.y = p.y;
      win.handle.w = p.w;
      win.handle.h = p.h;
      win.maximized = false;
      win.prev = null;
    } else {
      win.prev = { x: win.handle.x, y: win.handle.y, w: win.handle.w, h: win.handle.h };
      el.style.left = "0px";
      el.style.top = "0px";
      el.style.width = `${this.container.clientWidth}px`;
      el.style.height = `${this.container.clientHeight}px`;
      win.maximized = true;
    }
    this.focus(id);
    this.renderTaskbar();
    this.emitChange();
  }

  private render(id: string, win: WindowHandle, onMount?: (el: HTMLElement) => void) {
    const el = document.createElement("div");
    el.id = `win-${id}`;
    el.className = "pwindow";
    el.style.left = `${win.x}px`;
    el.style.top = `${win.y}px`;
    el.style.width = `${win.w}px`;
    el.style.height = `${win.h}px`;
    el.style.zIndex = String(++this.nextZ);

    el.innerHTML = `
      <div class="titlebar">
        <span class="title">${win.title}</span>
        <span class="controls">
          <span class="ctrl" data-action="minimize">_</span>
          <span class="ctrl" data-action="maximize">▢</span>
          <span class="ctrl close" data-action="close">✕</span>
        </span>
      </div>
      <div class="content"></div>
    `;

    const body = el.querySelector(".content") as HTMLElement;
    el.style.display = "flex";
    el.style.flexDirection = "column";
    if (win.content) body.appendChild(win.content);
    if (onMount) onMount(body);

    el.querySelector(".titlebar")?.addEventListener("mousedown", (e) => {
      const target = e.target as HTMLElement;
      if (target.classList.contains("ctrl")) return;
      this.focus(id);
      const w = this.windows.get(id);
      if (!w || w.maximized) return;
      this.dragState = {
        id,
        startX: (e as MouseEvent).clientX,
        startY: (e as MouseEvent).clientY,
        origX: w.handle.x,
        origY: w.handle.y,
      };
    });

    el.querySelectorAll<HTMLElement>(".ctrl").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        if (action === "close") this.close(id);
        else if (action === "minimize") this.minimize(id);
        else if (action === "maximize") this.toggleMaximize(id);
      });
    });

    const resizeHandle = document.createElement("div");
    resizeHandle.style.cssText =
      "position: absolute; bottom: 0; right: 0; width: 16px; height: 16px; cursor: nwse-resize; z-index: 1;";
    resizeHandle.addEventListener("mousedown", (e) => {
      const w = this.windows.get(id);
      if (!w || w.maximized) return;
      e.stopPropagation();
      this.focus(id);
      this.resizeState = {
        id,
        startX: (e as MouseEvent).clientX,
        startY: (e as MouseEvent).clientY,
        origW: w.handle.w,
        origH: w.handle.h,
      };
    });
    el.appendChild(resizeHandle);

    this.container.appendChild(el);
    this.focus(id);
  }

  private renderTaskbar() {
    this.taskbar.innerHTML = "";
    for (const w of this.windows.values()) {
      const btn = document.createElement("button");
      btn.className = "task" + (w.minimized ? " minimized" : "") + (w.maximized ? " maximized" : "");
      btn.textContent = w.handle.title;
      btn.addEventListener("click", () => {
        if (w.minimized) this.restore(w.id);
        else if (this.isFocused(w.id)) this.minimize(w.id);
        else this.focus(w.id);
      });
      this.taskbar.appendChild(btn);
    }
  }

  private isFocused(id: string): boolean {
    const w = this.windows.get(id);
    if (!w) return false;
    let topId = id;
    let topZ = -1;
    for (const [wid, win] of this.windows) {
      if (!win.minimized && (win.handle.zIndex ?? 0) > topZ) {
        topZ = win.handle.zIndex ?? 0;
        topId = wid;
      }
    }
    return topId === id;
  }

  private onMouseMove(e: MouseEvent) {
    if (this.dragState) {
      const w = this.windows.get(this.dragState.id);
      const el = document.getElementById(`win-${this.dragState.id}`);
      if (w && el) {
        w.handle.x = this.dragState.origX + (e.clientX - this.dragState.startX);
        w.handle.y = this.dragState.origY + (e.clientY - this.dragState.startY);
        el.style.left = `${w.handle.x}px`;
        el.style.top = `${w.handle.y}px`;
      }
    }
    if (this.resizeState) {
      const w = this.windows.get(this.resizeState.id);
      const el = document.getElementById(`win-${this.resizeState.id}`);
      if (w && el) {
        w.handle.w = Math.max(300, this.resizeState.origW + (e.clientX - this.resizeState.startX));
        w.handle.h = Math.max(200, this.resizeState.origH + (e.clientY - this.resizeState.startY));
        el.style.width = `${w.handle.w}px`;
        el.style.height = `${w.handle.h}px`;
      }
    }
  }

  private onMouseUp() {
    if (this.dragState) {
      this.dock(this.dragState.id);
      this.persist(this.dragState.id);
      this.dragState = null;
      this.emitChange();
    }
    if (this.resizeState) {
      this.persist(this.resizeState.id);
      this.resizeState = null;
      this.emitChange();
    }
  }

  private dock(id: string) {
    const w = this.windows.get(id);
    const el = document.getElementById(`win-${id}`);
    if (!w || !el) return;
    const snap = 24;
    const maxX = this.container.clientWidth - w.handle.w;
    const maxY = this.container.clientHeight - 28;
    if (w.handle.x <= snap) w.handle.x = 0;
    else if (w.handle.x >= maxX - snap) w.handle.x = Math.max(0, maxX);
    if (w.handle.y <= snap) w.handle.y = 0;
    else if (w.handle.y >= maxY - snap) w.handle.y = Math.max(0, maxY);
    el.style.left = `${w.handle.x}px`;
    el.style.top = `${w.handle.y}px`;
  }

  private persist(id: string) {
    const win = this.windows.get(id);
    if (!win) return;
    localStorage.setItem(
      `prometheus_window_${id}`,
      JSON.stringify({ x: win.handle.x, y: win.handle.y, w: win.handle.w, h: win.handle.h }),
    );
  }
}
