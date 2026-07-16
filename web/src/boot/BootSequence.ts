const BOOT_LOGO = `██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗
██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝
██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗
██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝
██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝`;

const BOOT_LINES = [
  "Initializing Platform",
  "Loading Knowledge Engine",
  "Loading Simulation Engine",
  "Loading Reasoning Engine",
  "Loading Agent Runtime",
  "Loading Hardware Layer",
  "Loading Plugins",
  "Loading User Workspace",
];

interface SystemData {
  version: string;
  services: number;
  plugins: number;
  agents: number;
  platform: string;
  stage_timings: Record<string, number>;
}

export class BootSequence {
  private el: HTMLElement;
  private onComplete: () => void;
  private bootSkipped = false;
  private timers: number[] = [];
  private rafs: number[] = [];
  private log: HTMLElement;
  private progressFill: HTMLElement;
  private timerEl: HTMLElement;
  private summaryEl: HTMLElement;
  private version = "1.0.0-rc1";
  private startTime = 0;
  private timerHandle = 0;
  private stageTimings: Record<string, number> = {};
  private data: SystemData = {
    version: "1.0.0-rc1",
    services: 0,
    plugins: 0,
    agents: 0,
    platform: "Stopped",
    stage_timings: {},
  };

  constructor(onComplete: () => void) {
    this.onComplete = onComplete;
    this.el = document.createElement("div");
    this.el.id = "boot";
    this.el.innerHTML = `
      <pre class="logo">${BOOT_LOGO}</pre>
      <div class="subtitle" id="boot-subtitle">ENGINEERING INTELLIGENCE PLATFORM &nbsp;·&nbsp; v${this.version}</div>
      <div id="boot-log">
        <div id="boot-progress" style="height:10px;background:var(--border);border:1px solid var(--border);border-radius:2px;overflow:hidden;margin:8px 0 2px;"><div id="boot-progress-fill" style="height:100%;width:0%;background:var(--yellow);transition:width 0.2s ease-out;"></div></div>
        <div id="boot-timer" style="font-family:var(--font-mono);color:var(--muted);font-size:12px;margin:6px 0 10px;text-align:left;">boot: 0.00s</div>
        <div id="boot-summary" style="display:none;margin:10px 0 4px;padding:8px 10px;border:1px solid var(--border);background:var(--panel);font-family:var(--font-mono);font-size:12px;color:var(--text);text-align:left;"></div>
      </div>
      <div id="boot-hint">press any key to skip<span class="cursor-blink">_</span></div>
    `;
    document.body.appendChild(this.el);
    this.log = this.el.querySelector("#boot-log") as HTMLElement;
    this.progressFill = this.el.querySelector("#boot-progress-fill") as HTMLElement;
    this.timerEl = this.el.querySelector("#boot-timer") as HTMLElement;
    this.summaryEl = this.el.querySelector("#boot-summary") as HTMLElement;
    document.addEventListener("keydown", this.onSkip, { once: true });
  }

  private onSkip = () => {
    this.bootSkipped = true;
    this.skip();
  };

  start() {
    this.startTime = performance.now();
    this.timerHandle = window.setInterval(() => this.updateTimer(), 60);

    const loadVersion = fetch("/version")
      .then((r) => r.json())
      .then((d) => {
        if (d && d.version) {
          this.version = String(d.version);
          this.data.version = this.version;
          const sub = this.el.querySelector("#boot-subtitle");
          if (sub) sub.textContent = `ENGINEERING INTELLIGENCE PLATFORM · v${this.version}`;
        }
      })
      .catch(() => {});

    const loadStatus = fetch("/status")
      .then((r) => r.json())
      .then((d) => {
        if (d) {
          if (typeof d.plugins === "number") this.data.plugins = d.plugins;
          if (typeof d.agents === "number") this.data.agents = d.agents;
          if (d.platform) this.data.platform = String(d.platform);
        }
      })
      .catch(() => {});

    const loadServices = fetch("/system/services")
      .then((r) => r.json())
      .then((d) => {
        if (d && Array.isArray(d.services)) this.data.services = d.services.length;
      })
      .catch(() => {});

    const loadHealth = fetch("/health")
      .then((r) => r.json())
      .then((d) => {
        if (d) {
          if (typeof d.plugins_loaded === "number") this.data.plugins = d.plugins_loaded;
          if (typeof d.agents_loaded === "number") this.data.agents = d.agents_loaded;
          if (d.platform_health && !this.data.platform) this.data.platform = String(d.platform_health);
        }
      })
      .catch(() => {});

    Promise.all([loadVersion, loadStatus, loadServices, loadHealth]).finally(() =>
      this.schedule(() => this.runBoot(0), 250)
    );
  }

  private updateTimer() {
    const elapsed = (performance.now() - this.startTime) / 1000;
    this.timerEl.textContent = `boot: ${elapsed.toFixed(2)}s`;
  }

  private freezeTimer() {
    if (this.timerHandle) window.clearInterval(this.timerHandle);
    this.timerHandle = 0;
    this.updateTimer();
  }

  private setProgress(pct: number) {
    const clamped = Math.max(0, Math.min(100, pct));
    this.progressFill.style.width = `${clamped}%`;
  }

  private schedule(fn: () => void, ms: number) {
    this.timers.push(window.setTimeout(fn, ms));
  }

  private typeLine(text: string, idx: number, cb: () => void) {
    const t0 = performance.now();
    const div = document.createElement("div");
    div.className = "line";
    this.log.appendChild(div);
    const raf = requestAnimationFrame(() => {
      const dots = ".".repeat(Math.max(16 - text.length, 3));
      div.innerHTML = `${text}${dots}<span class="ok">OK</span>`;
      this.setProgress(((idx + 1) / BOOT_LINES.length) * 100);
      this.data.stage_timings[text] = performance.now() - t0;
    });
    this.rafs.push(raf);
    this.schedule(cb, 90);
  }

  private renderSummary() {
    const running = /run/i.test(this.data.platform);
    const platformColor = running ? "#7CFC7C" : "var(--orange-red)";
    this.summaryEl.style.display = "block";
    const timingLines = Object.entries(this.data.stage_timings)
      .map(([k, v]) => `<div>${k}......... <span style="color:var(--text)">${v.toFixed(0)} ms</span></div>`)
      .join("");
    this.summaryEl.innerHTML = [
      `<div style="color:var(--yellow);margin-bottom:4px;font-family:var(--font-heading);font-size:10px;">SYSTEM SUMMARY</div>`,
      `<div>Version......... <span style="color:var(--text)">${this.data.version}</span></div>`,
      timingLines,
      `<div>Total........... <span style="color:var(--text)">${(Object.values(this.data.stage_timings).reduce((a, b) => a + b, 0) / 1000).toFixed(2)}s</span></div>`,
      `<div>Loaded Services. <span style="color:var(--text)">${this.data.services}</span></div>`,
      `<div>Plugins......... <span style="color:var(--text)">${this.data.plugins}</span></div>`,
      `<div>Agents.......... <span style="color:var(--text)">${this.data.agents}</span></div>`,
      `<div>Kernel.......... <span style="color:${platformColor}">${this.data.platform}</span></div>`,
    ].join("");
  }

  private runBoot(i: number) {
    if (this.bootSkipped) return;
    if (i >= BOOT_LINES.length) {
      this.setProgress(100);
      this.renderSummary();
      const done = document.createElement("div");
      done.className = "line prompt";
      done.textContent = "System Ready.";
      this.log.appendChild(done);
      this.schedule(() => {
        const launching = document.createElement("div");
        launching.className = "line prompt";
        launching.textContent = "Launching Workspace...";
        this.log.appendChild(launching);
        this.schedule(() => this.finish(), 400);
      }, 250);
      return;
    }
    this.typeLine(BOOT_LINES[i], i, () => this.runBoot(i + 1));
  }

  private skip() {
    this.timers.forEach((t) => clearTimeout(t));
    this.timers = [];
    this.rafs.forEach((r) => cancelAnimationFrame(r));
    this.rafs = [];
    this.log.innerHTML = "";
    this.setProgress(100);
    this.renderSummary();
    const done = document.createElement("div");
    done.className = "line prompt";
    done.textContent = "System Ready.";
    this.log.appendChild(done);
    const launching = document.createElement("div");
    launching.className = "line prompt";
    launching.textContent = "Launching Workspace...";
    this.log.appendChild(launching);
    this.schedule(() => this.finish(), 350);
  }

  private finish() {
    this.freezeTimer();
    document.removeEventListener("keydown", this.onSkip);
    this.el.style.opacity = "0";
    this.el.style.transition = "opacity 0.3s";
    this.schedule(() => {
      this.el.remove();
      this.onComplete();
    }, 300);
  }
}
