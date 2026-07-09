export interface WindowHandle {
  id: string;
  title: string;
  icon: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minimized: boolean;
  maximized: boolean;
  zIndex: number;
  content: HTMLElement;
  onClose?: () => void;
}

export class WindowManager {
  private windows: Map<string, WindowHandle> = new Map();
  private nextZ = 100;
  private container: HTMLElement;
  private dragState: { id: string; startX: number; startY: number; origX: number; origY: number } | null = null;
  private resizeState: { id: string; startX: number; startY: number; origW: number; origH: number; corner: string } | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
    this.container.addEventListener("mousemove", (e) => this.onMouseMove(e));
    this.container.addEventListener("mouseup", () => this.onMouseUp());
  }

  open(handle: Omit<WindowHandle, "id">, positionKey?: string) {
    const id = handle.title.toLowerCase().replace(/\s+/g, "-");
    const existing = localStorage.getItem(`prometheus_window_${id}`);
    let x = 80 + (this.windows.size * 30) % 200;
    let y = 60 + (this.windows.size * 30) % 150;
    let w = handle.w || 480;
    let h = handle.h || 320;
    if (existing) {
      try {
        const pos = JSON.parse(existing);
        x = pos.x ?? x;
        y = pos.y ?? y;
        w = pos.w ?? w;
        h = pos.h ?? h;
      } catch {}
    }
    const win: WindowHandle = {
      ...handle,
      id,
      x,
      y,
      w,
      h,
      minimized: false,
      maximized: false,
      zIndex: ++this.nextZ,
    };
    this.windows.set(id, win);
    this.render(win);
    this.focus(id);
    return id;
  }

  close(id: string) {
    const win = this.windows.get(id);
    if (win) {
      win.content.remove();
      this.windows.delete(id);
      win.onClose?.();
    }
  }

  focus(id: string) {
    const win = this.windows.get(id);
    if (win) {
      win.zIndex = ++this.nextZ;
      const el = document.getElementById(`win-${id}`);
      if (el) el.style.zIndex = String(win.zIndex);
    }
  }

  toggleMaximize(id: string) {
    const win = this.windows.get(id);
    if (!win) return;
    const el = document.getElementById(`win-${id}`);
    if (!el) return;
    if (win.maximized) {
      win.maximized = false;
      el.style.left = `${win.x}px`;
      el.style.top = `${win.y}px`;
      el.style.width = `${win.w}px`;
      el.style.height = `${win.h}px`;
    } else {
      win.maximized = true;
      el.style.left = "0px";
      el.style.top = "0px";
      el.style.width = "100%";
      el.style.height = "100%";
    }
    this.persist(id);
  }

  private render(win: WindowHandle) {
    const el = document.createElement("div");
    el.id = `win-${win.id}`;
    el.className = "window";
    el.style.left = `${win.x}px`;
    el.style.top = `${win.y}px`;
    el.style.width = `${win.w}px`;
    el.style.height = `${win.h}px`;
    el.style.zIndex = String(win.zIndex);

    el.innerHTML = `
      <div class="window-chrome" data-win="${win.id}">
        <span style="color: var(--text); font-size: 10px;">${win.icon} ${win.title}</span>
        <div class="window-controls">
          <button data-action="min">_</button>
          <button data-action="max">[]</button>
          <button data-action="close">X</button>
        </div>
      </div>
      <div class="window-body" style="flex: 1; overflow: auto;" data-win="${win.id}"></div>
    `;

    const body = el.querySelector(".window-body") as HTMLElement;
    el.style.display = "flex";
    el.style.flexDirection = "column";
    if (win.content) {
      body.appendChild(win.content);
    }

    el.querySelector(".window-chrome")?.addEventListener("mousedown", (e) => {
      if ((e.target as HTMLElement).dataset.action) return;
      this.focus(win.id);
      const clientX = (e as MouseEvent).clientX;
      const clientY = (e as MouseEvent).clientY;
      this.dragState = { id: win.id, startX: clientX, startY: clientY, origX: win.x, origY: win.y };
    });

    const closeBtn = el.querySelector<HTMLButtonElement>('button[data-action="close"]');
    closeBtn?.addEventListener("click", () => this.close(win.id));

    const minBtn = el.querySelector<HTMLButtonElement>('button[data-action="min"]');
    minBtn?.addEventListener("click", () => {
      el.style.display = win.minimized ? "flex" : "none";
      win.minimized = !win.minimized;
      if (!win.minimized) this.focus(win.id);
    });

    const maxBtn = el.querySelector<HTMLButtonElement>('button[data-action="max"]');
    maxBtn?.addEventListener("click", () => this.toggleMaximize(win.id));

    const resizeHandle = document.createElement("div");
    resizeHandle.style.cssText = "position: absolute; bottom: 0; right: 0; width: 16px; height: 16px; cursor: nwse-resize; z-index: 1;";
    resizeHandle.addEventListener("mousedown", (e) => {
      e.stopPropagation();
      this.focus(win.id);
      this.resizeState = { id: win.id, startX: (e as MouseEvent).clientX, startY: (e as MouseEvent).clientY, origW: win.w, origH: win.h, corner: "se" };
    });
    el.appendChild(resizeHandle);

    this.container.appendChild(el);
    this.focus(win.id);
  }

  private onMouseMove(e: MouseEvent) {
    if (this.dragState) {
      const win = this.windows.get(this.dragState.id);
      const el = document.getElementById(`win-${this.dragState.id}`);
      if (win && el && !win.maximized) {
        const dx = e.clientX - this.dragState.startX;
        const dy = e.clientY - this.dragState.startY;
        win.x = this.dragState.origX + dx;
        win.y = this.dragState.origY + dy;
        el.style.left = `${win.x}px`;
        el.style.top = `${win.y}px`;
      }
    }
    if (this.resizeState) {
      const win = this.windows.get(this.resizeState.id);
      const el = document.getElementById(`win-${this.resizeState.id}`);
      if (win && el && !win.maximized) {
        const dx = e.clientX - this.resizeState.startX;
        const dy = e.clientY - this.resizeState.startY;
        win.w = Math.max(300, this.resizeState.origW + dx);
        win.h = Math.max(200, this.resizeState.origH + dy);
        el.style.width = `${win.w}px`;
        el.style.height = `${win.h}px`;
      }
    }
  }

  private onMouseUp() {
    if (this.dragState) {
      this.persist(this.dragState.id);
      this.dragState = null;
    }
    if (this.resizeState) {
      this.persist(this.resizeState.id);
      this.resizeState = null;
    }
  }

  private persist(id: string) {
    const win = this.windows.get(id);
    if (!win) return;
    localStorage.setItem(`prometheus_window_${id}`, JSON.stringify({ x: win.x, y: win.y, w: win.w, h: win.h }));
  }
}
