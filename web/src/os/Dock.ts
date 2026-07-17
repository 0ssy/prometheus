import { kernel } from "../kernel/KernelClient";

export interface DockItem {
  id: string;
  title: string;
  icon: string;
  badge?: number;
  running?: boolean;
  pinned?: boolean;
}

export class Dock {
  private el: HTMLElement;
  private items: DockItem[] = [];
  private contextTarget: DockItem | null = null;
  private listeners: { [type: string]: Set<(e: any) => void> } = {};

  constructor(el: HTMLElement) {
    this.el = el;
    this.el.className = "dock";
    this.el.innerHTML = `<div id="dock-list" style="display:flex; gap:6px; align-items:center; padding:4px 8px;"></div>`;
    this.el.addEventListener("contextmenu", (e) => this.onContext(e));
  }

  addEventListener(type: string, handler: (e: any) => void) {
    if (!this.listeners[type]) this.listeners[type] = new Set();
    this.listeners[type].add(handler);
  }

  removeEventListener(type: string, handler: (e: any) => void) {
    this.listeners[type]?.delete(handler);
  }

  private dispatch(type: string, detail: any) {
    this.listeners[type]?.forEach((h) => h({ detail }));
  }

  setItems(items: DockItem[]) {
    this.items = items;
    this.render();
  }

  private render() {
    const list = this.el.querySelector("#dock-list") as HTMLElement;
    list.innerHTML = "";
    for (const item of this.items) {
      const btn = document.createElement("button");
      btn.className = "dock-item" + (item.running ? " running" : "") + (item.pinned ? " pinned" : "");
      btn.dataset.id = item.id;
      btn.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 12 12" style="vertical-align:-2px;margin-right:4px;">${item.icon}</svg>
        <span>${item.title}</span>
        ${item.running ? '<span class="dock-running-dot"></span>' : ""}
        ${item.badge && item.badge > 0 ? `<span class="dock-badge">${item.badge}</span>` : ""}
      `;
      btn.addEventListener("click", () => {
        if (item.pinned) {
          this.onOpen(item);
        }
      });
      btn.addEventListener("dblclick", () => {
        this.onOpen(item);
      });
      list.appendChild(btn);
    }
  }

  private onOpen(item: DockItem) {
    if (item.running) {
      this.dispatch("dock:focus", { id: item.id });
    } else {
      this.dispatch("dock:open", { id: item.id });
    }
  }

  private onContext(e: MouseEvent) {
    const btn = (e.target as HTMLElement).closest("[data-id]") as HTMLElement | null;
    if (!btn) return;
    e.preventDefault();
    const id = btn.dataset.id!;
    const item = this.items.find((i) => i.id === id);
    if (!item) return;
    this.contextTarget = item;
    const menu = document.createElement("div");
    menu.className = "dock-context-menu";
    menu.innerHTML = `
      <div class="dock-menu-item" data-action="open">Open</div>
      ${item.running ? '<div class="dock-menu-item" data-action="close">Close All</div>' : ""}
      <div class="dock-menu-item" data-action="recent">Recent</div>
      <div class="dock-menu-sep"></div>
      <div class="dock-menu-item" data-action="pin">${item.pinned ? "Unpin" : "Pin"}</div>
      <div class="dock-menu-item" data-action="remove">Remove from Dock</div>
    `;
    menu.style.left = `${e.clientX}px`;
    menu.style.top = `${e.clientY}px`;
    document.body.appendChild(menu);
    const closeMenu = () => menu.remove();
    menu.addEventListener("click", (ev) => {
      const action = (ev.target as HTMLElement).dataset.action;
      if (action === "open") this.onOpen(item);
      else if (action === "close") {
        this.dispatch("dock:close", { id: item.id });
      } else if (action === "recent") {
        this.dispatch("dock:recent", { id: item.id });
      }       else if (action === "pin") {
        item.pinned = !item.pinned;
        this.render();
        kernel.sessionSave?.({ pinned: this.items.filter((i) => i.pinned).map((i) => i.id) } as any).catch(() => {});
      } else if (action === "remove") {
        this.items = this.items.filter((i) => i.id !== item.id);
        this.render();
      }
      closeMenu();
    });
    setTimeout(() => document.addEventListener("click", closeMenu, { once: true }), 0);
  }

  setBadge(id: string, count: number) {
    const item = this.items.find((i) => i.id === id);
    if (item) {
      item.badge = count;
      this.render();
    }
  }

  setRunning(id: string, running: boolean) {
    const item = this.items.find((i) => i.id === id);
    if (item) {
      item.running = running;
      this.render();
    }
  }
}
