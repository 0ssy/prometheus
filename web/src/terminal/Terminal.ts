import { sdk } from "../sdk";
import { kernel } from "../kernel/KernelClient";

export interface TerminalContext {
  openApp: (id: string) => void;
  logActivity: (text: string) => void;
}

interface TerminalSession {
  id: string;
  tab: HTMLButtonElement;
  view: HTMLDivElement;
  buffer: string;
  shell: string;
  cols: number;
  rows: number;
  searchQuery: string;
}

const ANSI_8: Record<number, string> = {
  0: "#000000",
  1: "#cd3131",
  2: "#0dbc79",
  3: "#e5e510",
  4: "#2472c8",
  5: "#bc3fbc",
  6: "#11a8cd",
  7: "#e5e5e5",
};
const ANSI_16: Record<number, string> = {
  0: "#666666",
  1: "#f14c4c",
  2: "#23d18b",
  3: "#f5f543",
  4: "#3b8eea",
  5: "#d670d6",
  6: "#29b8db",
  7: "#ffffff",
};

function defaultShell(): string {
  if (typeof navigator !== "undefined" && /Win/i.test(navigator.platform)) {
    return "pwsh";
  }
  return "bash";
}

export class Terminal {
  private termbar: HTMLElement;
  private ctx: TerminalContext;
  private tabsEl!: HTMLDivElement;
  private viewsEl!: HTMLDivElement;
  private toolbar!: HTMLDivElement;
  private input!: HTMLInputElement;
  private sessions: TerminalSession[] = [];
  private active: TerminalSession | null = null;
  private history: string[] = [];
  private historyIdx = -1;
  private native = false;
  private unlisten: Array<() => void> = [];
  private splitActive = false;

  constructor(termbar: HTMLElement, ctx: TerminalContext) {
    this.termbar = termbar;
    this.ctx = ctx;
    this.render();
    this.native = sdk.kernel.isNative();
    this.subscribeOutput();
    this.newTab();
  }

  private render() {
    this.termbar.innerHTML = `
      <div id="term-toolbar" style="display:flex; gap:6px; align-items:center; padding:2px 4px; border-bottom:1px solid var(--border);">
        <select id="term-shell" style="background:var(--bg); color:var(--text); border:1px solid var(--border); font-family:var(--font-mono); font-size:11px; padding:1px 4px;">
          <option value="pwsh">PowerShell</option>
          <option value="cmd">CMD</option>
          <option value="bash">bash</option>
          <option value="zsh">zsh</option>
          <option value="sh">sh</option>
        </select>
        <button id="term-new" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:1px 6px; cursor:pointer; font-size:11px;">+</button>
        <button id="term-split" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:1px 6px; cursor:pointer; font-size:11px;">Split</button>
        <button id="term-find" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:1px 6px; cursor:pointer; font-size:11px;">Find</button>
        <input id="term-search" style="display:none; background:var(--bg); color:var(--text); border:1px solid var(--border); padding:1px 4px; font-family:var(--font-mono); font-size:11px;" placeholder="find..." />
        <span id="term-mode" style="margin-left:auto; font-family:var(--font-mono); font-size:10px; padding:1px 6px; border:1px solid var(--border); color:${this.native ? "var(--green)" : "var(--orange)"};">${this.native ? "NATIVE" : "BROWSER"}</span>
      </div>
      <div id="term-tabs" class="term-tabs" style="display:flex; gap:2px; padding:2px 4px; border-bottom:1px solid var(--border);"></div>
      <div id="term-views" class="term-views" style="flex:1; display:flex; min-height:0;"></div>
      <div id="terminput-row" style="display:flex; gap:6px; padding:2px 4px; border-top:1px solid var(--border);">
        <span class="prompt" style="color:var(--yellow); font-family:var(--font-mono); font-size:12px;">&gt;</span>
        <input id="terminput" type="text" autocomplete="off" spellcheck="false" style="flex:1; background:transparent; color:var(--text); border:none; outline:none; font-family:var(--font-mono); font-size:12px;" placeholder="type a command, or a Prometheus shortcut (open <app>, show devices, run simulation, help)..." />
      </div>`;
    this.tabsEl = this.termbar.querySelector("#term-tabs") as HTMLDivElement;
    this.viewsEl = this.termbar.querySelector("#term-views") as HTMLDivElement;
    this.toolbar = this.termbar.querySelector("#term-toolbar") as HTMLDivElement;
    this.input = this.termbar.querySelector("#terminput") as HTMLInputElement;

    this.input.addEventListener("keydown", (e) => this.onInputKey(e));

    (this.termbar.querySelector("#term-new") as HTMLElement).addEventListener("click", () => this.newTab());
    (this.termbar.querySelector("#term-split") as HTMLElement).addEventListener("click", () => {
      this.splitActive = !this.splitActive;
      this.selectTab(this.active!);
    });
    (this.termbar.querySelector("#term-find") as HTMLElement).addEventListener("click", () => {
      const search = this.termbar.querySelector("#term-search") as HTMLInputElement;
      search.style.display = search.style.display === "none" ? "block" : "none";
      if (search.style.display === "block") search.focus();
    });

    const searchInput = this.termbar.querySelector("#term-search") as HTMLInputElement;
    searchInput.addEventListener("input", () => {
      const query = searchInput.value.trim();
      const sess = this.active;
      if (sess) this.highlightSearch(sess, query);
    });

    (this.termbar.querySelector("#term-shell") as HTMLSelectElement).addEventListener("change", (e) => {
      const sess = this.active;
      if (sess && this.native) {
        sdk.kernel.terminalKill(sess.id).then(() => {
          const shell = (e.target as HTMLSelectElement).value;
          sdk.kernel.terminalSpawn(shell, sess.cols, sess.rows).then((id) => {
            sess.id = id;
            sess.shell = shell;
            sess.buffer = "";
            this.renderInto(sess.view, `prometheus terminal — ${shell}\r\n`);
          });
        });
      }
    });

    if (!this.native) {
      this.banner("Browser mode: terminal input is echoed locally. Run the desktop build for a real PTY (PowerShell/Bash).");
    }
  }

  private subscribeOutput() {
    kernel
      .listen<{ target?: string; payload?: { data?: string } }>("terminal-output", (ev) => {
        const b64 = ev?.payload?.data;
        if (!b64) return;
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
        const text = new TextDecoder().decode(bytes);
        const sid = ev?.target;
        const sess = sid ? this.sessions.find((s) => s.id === sid) : this.active;
        if (sess) this.appendOutput(sess, text);
      })
      .then((off) => this.unlisten.push(off))
      .catch(() => {});
  }

  private appendOutput(sess: TerminalSession, text: string) {
    sess.buffer += text;
    this.renderInto(sess.view, sess.buffer);
    this.highlightSearch(sess, sess.searchQuery);
    sess.view.scrollTop = sess.view.scrollHeight;
  }

  private highlightSearch(sess: TerminalSession, query: string) {
    sess.searchQuery = query;
    sess.view.querySelectorAll(".search-match").forEach((el) => el.classList.remove("search-match"));
    if (!query || !sess.buffer) return;
    const lowerBuf = sess.buffer.toLowerCase();
    const lowerQuery = query.toLowerCase();
    let idx = lowerBuf.indexOf(lowerQuery);
    while (idx !== -1) {
      const range = document.createRange();
      const walker = document.createTreeWalker(sess.view, NodeFilter.SHOW_TEXT, null);
      let currentOffset = 0;
      while (true) {
        const node = walker.nextNode();
        if (!node) break;
        const nodeLen = (node as Text).nodeValue?.length || 0;
        if (currentOffset + nodeLen > idx) {
          const startInNode = idx - currentOffset;
          const endInNode = Math.min(startInNode + query.length, nodeLen);
          try {
            range.setStart(node, startInNode);
            range.setEnd(node, endInNode);
            const span = document.createElement("span");
            span.className = "search-match";
            span.style.background = "var(--yellow)";
            span.style.color = "var(--bg)";
            range.surroundContents(span);
          } catch {}
          break;
        }
        currentOffset += nodeLen;
      }
      idx = lowerBuf.indexOf(lowerQuery, idx + 1);
    }
  }

  private renderInto(view: HTMLElement, raw: string) {
    view.innerHTML = this.renderAnsiHtml(raw);
  }

  private renderAnsiHtml(raw: string): string {
    const lines = raw.split("\n");
    let html = "";
    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
      if (lineIdx > 0) html += "\n";
      html += this.parseAnsiToHtml(lines[lineIdx]);
    }
    return html;
  }

  private parseAnsiToHtml(line: string): string {
    let i = 0;
    let buf = "";
    let curFg = "";
    let curBold = false;
    let html = "";
    const flush = () => {
      if (!buf) return;
      const escaped = buf.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      html += curFg || curBold ? `<span style="color:${curFg || "inherit"};${curBold ? "font-weight:bold;" : ""}">${escaped}</span>` : escaped;
      buf = "";
    };
    while (i < line.length) {
      if (line[i] === "\x1b" && line[i + 1] === "[") {
        let j = i + 2;
        let num = "";
        while (j < line.length && /[0-9;]/.test(line[j])) {
          num += line[j];
          j++;
        }
        if (line[j] === "m") {
          flush();
          for (const code of num.split(";").filter((c) => c !== "")) {
            const n = parseInt(code, 10);
            if (n === 0) {
              curFg = "";
              curBold = false;
            } else if (n === 1) {
              curBold = true;
            } else if (n >= 30 && n <= 37) {
              curFg = ANSI_8[n - 30];
            } else if (n === 39) {
              curFg = "";
            } else if (n >= 90 && n <= 97) {
              curFg = ANSI_16[n - 90];
            }
          }
          i = j + 1;
          continue;
        }
      }
      buf += line[i];
      i++;
    }
    flush();
    return html;
  }

  private onInputKey(e: KeyboardEvent) {
    if (e.key === "Enter") {
      const val = this.input.value;
      this.input.value = "";
      this.submit(val);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this.historyNav(-1);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      this.historyNav(1);
    } else if (e.key === "c" && (e.ctrlKey || e.metaKey)) {
      this.sendRaw("\x03");
    } else if (e.key === "l" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      this.clear();
    }
  }

  private historyNav(dir: number) {
    if (this.history.length === 0) return;
    this.historyIdx += dir;
    if (this.historyIdx < 0) this.historyIdx = 0;
    if (this.historyIdx >= this.history.length) {
      this.historyIdx = this.history.length;
      this.input.value = "";
      return;
    }
    this.input.value = this.history[this.history.length - 1 - this.historyIdx];
  }

  private async submit(val: string) {
    const line = val.replace(/\r?\n$/, "");
    if (line.trim()) {
      this.history.push(line);
      sdk.kernel.terminalRecordCommand(this.activeId(), line).catch(() => {});
    }
    this.echo("> " + line);
    if (this.tryShortcut(line)) return;
    await this.sendRaw(line + "\n");
  }

  private async sendRaw(text: string) {
    if (!this.active) return;
    try {
      await sdk.kernel.terminalWrite(this.active.id, text);
    } catch {
      // Browser mode
    }
  }

  private echo(text: string) {
    if (this.active) this.appendOutput(this.active, text + "\n");
  }

  private clear() {
    if (this.active) {
      this.active.buffer = "";
      this.renderInto(this.active.view, "");
    }
  }

  private tryShortcut(raw: string): boolean {
    const val = raw.toLowerCase().trim();
    const stripped = val.startsWith("prometheus ") ? val.slice("prometheus ".length) : val;

    if (stripped.startsWith("open ")) {
      this.ctx.openApp(stripped.slice(5).trim().toLowerCase());
      return true;
    }
    switch (stripped) {
      case "help":
        this.echo("shortcuts: open <app> · show devices · list agents · run simulation · search <query> · build digital-twin <device> · explain kernel · help");
        return true;
      case "show devices":
      case "list devices":
        this.ctx.openApp("devices");
        return true;
      case "run simulation":
        this.ctx.openApp("simulation");
        this.ctx.logActivity("Simulation Completed");
        sdk.simulation.run("esp32_01", "disconnect").catch(() => {});
        return true;
      case "list agents":
        sdk.agents.list().then((a: any) => {
          const names = (a.agents ?? []).map((x: any) => x.name).join(", ") || "none";
          this.echo("agents: " + names);
        }).catch((e: any) => this.echo("agents lookup failed: " + (e?.message ?? e)));
        return true;
      case "explain kernel":
        this.echo("kernel boots config -> plugins -> devices -> agents -> knowledge graph -> scheduler.");
        return true;
    }
    if (stripped.startsWith("search ")) {
      this.ctx.openApp("knowledge");
      return true;
    }
    if (stripped.startsWith("build digital-twin")) {
      this.ctx.openApp("simulation");
      this.ctx.logActivity("Digital Twin Built");
      return true;
    }
    if (stripped.startsWith("connect ")) {
      const dev = stripped.slice(8).trim();
      sdk.hardware.connect(dev, "usb").then(() => this.ctx.logActivity("Device Connected")).catch(() => {});
      return true;
    }
    return false;
  }

  private async newTab(shell?: string) {
    const shellSelect = this.termbar.querySelector("#term-shell") as HTMLSelectElement | null;
    const chosen = shell ?? (shellSelect?.value || defaultShell());

    const tab = document.createElement("button");
    tab.className = "term-tab";
    const label = document.createElement("span");
    tab.appendChild(label);
    const close = document.createElement("span");
    close.className = "term-tab-close";
    close.textContent = "×";
    close.addEventListener("click", (e) => {
      e.stopPropagation();
      this.closeTab(sess);
    });
    tab.appendChild(close);

    const view = document.createElement("div");
    view.className = "term-view";

    const sess: TerminalSession = {
      id: "pending",
      tab,
      view,
      buffer: "",
      shell: chosen,
      cols: 80,
      rows: 24,
      searchQuery: "",
    };

    tab.addEventListener("click", () => this.selectTab(sess));

    this.tabsEl.appendChild(tab);
    this.viewsEl.appendChild(view);
    this.sessions.push(sess);

    if (this.native) {
      try {
        const id = await sdk.kernel.terminalSpawn(chosen, 80, 24);
        sess.id = id;
        label.textContent = chosen;
        this.appendOutput(sess, `prometheus terminal — ${chosen}\r\n`);
      } catch (e: any) {
        label.textContent = "error";
        this.appendOutput(sess, "failed to spawn PTY: " + (e?.message ?? String(e)) + "\r\n");
      }
    } else {
      sess.id = "local-" + Math.random().toString(36).slice(2, 8);
      label.textContent = chosen;
      this.appendOutput(sess, `prometheus terminal (simulated) — ${chosen}\r\n`);
    }
    this.selectTab(sess);
  }

  private selectTab(sess: TerminalSession) {
    this.active = sess;
    for (const s of this.sessions) {
      s.tab.classList.toggle("active", s === sess);
      s.view.style.display = s === sess ? (this.splitActive ? "flex" : "block") : "none";
      if (this.splitActive && s === sess) {
        s.view.style.flex = "1";
        s.view.style.flexDirection = "column";
      }
    }
    this.input.focus();
  }

  private async closeTab(sess: TerminalSession) {
    if (this.sessions.length <= 1) return;
    try {
      await sdk.kernel.terminalKill(sess.id);
    } catch {}
    sess.tab.remove();
    sess.view.remove();
    this.sessions = this.sessions.filter((s) => s !== sess);
    if (this.active === sess) this.selectTab(this.sessions[0]);
  }

  private activeId(): string {
    return this.active?.id ?? "";
  }

  logGui(text: string) {
    this.echo(text);
  }

  private banner(text: string) {
    if (this.sessions[0]) this.appendOutput(this.sessions[0], text + "\r\n");
  }
}
