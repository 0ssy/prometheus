import { kernel } from "../kernel/KernelClient";
import { api } from "../api/client";

export interface TerminalContext {
  openApp: (id: string) => void;
  logActivity: (text: string) => void;
}

interface TerminalSession {
  id: string; // kernel PTY session id
  tab: HTMLButtonElement;
  view: HTMLDivElement; // scrollback <pre>
  buffer: string; // raw accumulated text (for find/search)
}

/** Pick the first shell that is plausibly available on this platform. */
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
  private input!: HTMLInputElement;
  private sessions: TerminalSession[] = [];
  private active: TerminalSession | null = null;
  private history: string[] = [];
  private historyIdx = -1;
  private native = false;
  private unlisten: Array<() => void> = [];

  constructor(termbar: HTMLElement, ctx: TerminalContext) {
    this.termbar = termbar;
    this.ctx = ctx;
    this.render();
    this.native = kernel.isNative();
    this.subscribeOutput();
    this.newTab();
  }

  private render() {
    this.termbar.innerHTML = `
      <div id="term-tabs" class="term-tabs"></div>
      <div id="term-views" class="term-views"></div>
      <div id="terminput-row"><span class="prompt">&gt;</span><input id="terminput" type="text" autocomplete="off" spellcheck="false" placeholder="type a command, or a Prometheus shortcut (open <app>, show devices, run simulation, help)..."/></div>`;
    this.tabsEl = this.termbar.querySelector("#term-tabs") as HTMLDivElement;
    this.viewsEl = this.termbar.querySelector("#term-views") as HTMLDivElement;
    this.input = this.termbar.querySelector("#terminput") as HTMLInputElement;

    this.input.addEventListener("keydown", (e) => this.onInputKey(e));

    if (!this.native) {
      this.banner(
        "Browser mode: terminal input is echoed locally. Run the desktop build for a real PTY (PowerShell/Bash).",
      );
    }
  }

  // --- Output streaming -------------------------------------------------------

  private subscribeOutput() {
    // The kernel emits a `KernelEvent` { topic, target, payload: { data } };
    // Tauri forwards it as the event payload, so the handler receives the
    // KernelEvent directly. `target` is the session id; `payload.data` is the
    // base64-encoded PTY bytes.
    kernel
      .listen<{ target?: string; payload?: { data?: string } }>("terminal-output", (ev) => {
        const b64 = ev?.payload?.data;
        if (!b64) return;
        const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
        const text = new TextDecoder().decode(bytes);
        const sid = ev?.target;
        const sess = sid
          ? this.sessions.find((s) => s.id === sid)
          : this.active;
        if (sess) this.appendOutput(sess, text);
      })
      .then((off) => this.unlisten.push(off))
      .catch(() => {});
  }

  private appendOutput(sess: TerminalSession, text: string) {
    sess.buffer += text;
    // Render incrementally: parse ANSI into styled spans.
    this.renderInto(sess.view, sess.buffer);
    sess.view.scrollTop = sess.view.scrollHeight;
  }

  /** Render raw text (with ANSI escapes) into a <pre> using styled spans. */
  private renderInto(view: HTMLElement, raw: string) {
    view.textContent = "";
    const lines = raw.split("\n");
    let fg = "";
    let bold = false;
    let lineNo = 0;
    for (const line of lines) {
      if (lineNo++ > 0) view.appendChild(document.createTextNode("\n"));
      const frag = this.parseAnsi(line, fg, bold, (n, b) => {
        fg = n;
        bold = b;
      });
      view.appendChild(frag);
    }
  }

  /** Minimal ANSI SGR parser -> DocumentFragment of styled spans.
   *  `fg`/`bold` carry the current style into the line; the setter persists
   *  style changes back to the caller across lines. */
  private parseAnsi(
    line: string,
    fg: string,
    bold: boolean,
    setStyle: (fg: string, bold: boolean) => void,
  ): DocumentFragment {
    const frag = document.createDocumentFragment();
    let i = 0;
    let buf = "";
    let curFg = fg;
    let curBold = bold;
    const flush = () => {
      if (!buf) return;
      const span = document.createElement("span");
      if (curFg) span.style.color = curFg;
      if (curBold) span.style.fontWeight = "bold";
      span.textContent = buf;
      frag.appendChild(span);
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
            // background codes (40-47/100-107) ignored for simplicity.
          }
          setStyle(curFg, curBold);
        }
        i = j + 1;
        continue;
      }
      buf += line[i];
      i++;
    }
    flush();
    return frag;
  }

  // --- Input -----------------------------------------------------------------

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
      // Ctrl+C -> forward to PTY as ETX.
      this.sendRaw("\x03");
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
      kernel.terminalRecordCommand(this.activeId(), line).catch(() => {});
    }
    // Echo locally for immediate feedback.
    this.echo("> " + line);
    // Try Prometheus command shortcuts first (GUI bridge).
    if (this.tryShortcut(line)) return;
    // Otherwise send to the PTY.
    await this.sendRaw(line + "\n");
  }

  private async sendRaw(text: string) {
    if (!this.active) return;
    try {
      await kernel.terminalWrite(this.active.id, text);
    } catch {
      // Browser mode: nothing to forward.
    }
  }

  private echo(text: string) {
    if (this.active) this.appendOutput(this.active, text + "\n");
  }

  /** Prometheus desktop shortcuts that open GUI apps / run actions. */
  private tryShortcut(raw: string): boolean {
    const val = raw.toLowerCase().trim();
    const stripped = val.startsWith("prometheus ")
      ? val.slice("prometheus ".length)
      : val;

    if (stripped.startsWith("open ")) {
      this.ctx.openApp(stripped.slice(5).trim().toLowerCase());
      return true;
    }
    switch (stripped) {
      case "help":
        this.echo(
          "shortcuts: open <app> · show devices · list agents · run simulation · search <query> · build digital-twin <device> · explain kernel · help",
        );
        return true;
      case "show devices":
      case "list devices":
        this.ctx.openApp("devices");
        return true;
      case "run simulation":
        this.ctx.openApp("simulation");
        this.ctx.logActivity("Simulation Completed");
        api
          .simulationRun("esp32_01", "disconnect")
          .catch(() => {});
        return true;
      case "list agents":
        api
          .agents()
          .then((a: any) => {
            const names = (a.agents ?? []).map((x: any) => x.name).join(", ") || "none";
            this.echo("agents: " + names);
          })
          .catch((e: any) => this.echo("agents lookup failed: " + e.message));
        return true;
      case "explain kernel":
        this.echo(
          "kernel boots config -> plugins -> devices -> agents -> knowledge graph -> scheduler.",
        );
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
      api
        .devicesSimulated(dev)
        .then(() => this.ctx.logActivity("Device Connected"))
        .catch(() => {});
      return true;
    }
    return false;
  }

  // --- Tabs ------------------------------------------------------------------

  private async newTab(shell?: string) {
    const chosen = shell ?? defaultShell();

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
    };

    tab.addEventListener("click", () => this.selectTab(sess));

    this.tabsEl.appendChild(tab);
    this.viewsEl.appendChild(view);
    this.sessions.push(sess);

    if (this.native) {
      try {
        const id = await kernel.terminalSpawn(chosen, 120, 30);
        sess.id = id;
        label.textContent = chosen;
        this.appendOutput(sess, `prometheus terminal — ${chosen}\r\n`);
      } catch (e: any) {
        label.textContent = "error";
        this.appendOutput(sess, "failed to spawn PTY: " + e.message + "\r\n");
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
      s.view.style.display = s === sess ? "block" : "none";
    }
    this.input.focus();
  }

  private async closeTab(sess: TerminalSession) {
    if (this.sessions.length <= 1) return; // keep at least one
    try {
      await kernel.terminalKill(sess.id);
    } catch {}
    sess.tab.remove();
    sess.view.remove();
    this.sessions = this.sessions.filter((s) => s !== sess);
    if (this.active === sess) this.selectTab(this.sessions[0]);
  }

  private activeId(): string {
    return this.active?.id ?? "";
  }

  // --- Public API used by Desktop -------------------------------------------

  /** Reflect a GUI-originated action into the terminal (two-way bridge). */
  logGui(text: string) {
    this.echo(text);
  }

  private banner(text: string) {
    if (this.sessions[0]) this.appendOutput(this.sessions[0], text + "\r\n");
  }
}

// 8/16-color ANSI palette (CSS hex) for lightweight rendering.
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
