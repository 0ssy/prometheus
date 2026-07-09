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

export class WindowManager {
  private windows: Map<string, WindowHandle> = new Map();
  private nextZ = 100;
  private container: HTMLElement;
  private dragState: { id: string; startX: number; startY: number; origX: number; origY: number } | null = null;
  private resizeState: { id: string; startX: number; startY: number; origW: number; origH: number } | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
    this.container.addEventListener("mousemove", (e) => this.onMouseMove(e));
    this.container.addEventListener("mouseup", () => this.onMouseUp());
  }

  open(id: string, handle: WindowHandle, onMount?: (el: HTMLElement) => void): string {
    const existing = this.windows.get(id);
    if (existing) {
      this.focus(id);
      const el = document.getElementById(`win-${id}`);
      if (el) el.style.display = "flex";
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
    this.windows.set(id, win);
    this.render(id, win, onMount);
    return id;
  }

  close(id: string) {
    const win = this.windows.get(id);
    if (win) {
      const el = document.getElementById(`win-${id}`);
      el?.remove();
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

  isOpen(id: string): boolean {
    return this.windows.has(id);
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
        <span class="close" data-action="close">✕</span>
      </div>
      <div class="content"></div>
    `;

    const body = el.querySelector(".content") as HTMLElement;
    el.style.display = "flex";
    el.style.flexDirection = "column";
    if (win.content) body.appendChild(win.content);
    if (onMount) onMount(body);

    el.querySelector(".titlebar")?.addEventListener("mousedown", (e) => {
      this.focus(id);
      this.dragState = {
        id,
        startX: (e as MouseEvent).clientX,
        startY: (e as MouseEvent).clientY,
        origX: win.x,
        origY: win.y,
      };
    });

    const closeBtn = el.querySelector<HTMLElement>('.close[data-action="close"]');
    closeBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.close(id);
    });

    const resizeHandle = document.createElement("div");
    resizeHandle.style.cssText =
      "position: absolute; bottom: 0; right: 0; width: 16px; height: 16px; cursor: nwse-resize; z-index: 1;";
    resizeHandle.addEventListener("mousedown", (e) => {
      e.stopPropagation();
      this.focus(id);
      this.resizeState = {
        id,
        startX: (e as MouseEvent).clientX,
        startY: (e as MouseEvent).clientY,
        origW: win.w,
        origH: win.h,
      };
    });
    el.appendChild(resizeHandle);

    this.container.appendChild(el);
    this.focus(id);
  }

  private onMouseMove(e: MouseEvent) {
    if (this.dragState) {
      const win = this.windows.get(this.dragState.id);
      const el = document.getElementById(`win-${this.dragState.id}`);
      if (win && el) {
        win.x = this.dragState.origX + (e.clientX - this.dragState.startX);
        win.y = this.dragState.origY + (e.clientY - this.dragState.startY);
        el.style.left = `${win.x}px`;
        el.style.top = `${win.y}px`;
      }
    }
    if (this.resizeState) {
      const win = this.windows.get(this.resizeState.id);
      const el = document.getElementById(`win-${this.resizeState.id}`);
      if (win && el) {
        win.w = Math.max(300, this.resizeState.origW + (e.clientX - this.resizeState.startX));
        win.h = Math.max(200, this.resizeState.origH + (e.clientY - this.resizeState.startY));
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
