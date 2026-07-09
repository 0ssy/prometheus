const BOOT_LOGO = `██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗
██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝
██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗
██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝
██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝`;

const BOOT_LINES = [
  "Initializing Kernel",
  "Loading Knowledge Engine",
  "Loading Simulation Engine",
  "Loading Reasoning Engine",
  "Loading Agent Runtime",
  "Loading Hardware Layer",
  "Loading Plugins",
  "Loading User Workspace",
];

export class BootSequence {
  private el: HTMLElement;
  private onComplete: () => void;
  private bootSkipped = false;
  private timers: number[] = [];
  private log: HTMLElement;
  private version = "0.6.0";

  constructor(onComplete: () => void) {
    this.onComplete = onComplete;
    this.el = document.createElement("div");
    this.el.id = "boot";
    this.el.innerHTML = `
      <pre class="logo">${BOOT_LOGO}</pre>
      <div class="subtitle" id="boot-subtitle">ENGINEERING INTELLIGENCE OS &nbsp;·&nbsp; v${this.version}</div>
      <div id="boot-log"></div>
      <div id="boot-hint">press any key to skip<span class="cursor-blink">_</span></div>
    `;
    document.body.appendChild(this.el);
    this.log = this.el.querySelector("#boot-log") as HTMLElement;
    document.addEventListener("keydown", this.onSkip, { once: true });
  }

  private onSkip = () => {
    this.bootSkipped = true;
    this.skip();
  };

  start() {
    const done = () => this.schedule(() => this.runBoot(0), 400);
    fetch("/version")
      .then((r) => r.json())
      .then((d) => {
        if (d && d.version) {
          this.version = String(d.version);
          const sub = this.el.querySelector("#boot-subtitle");
          if (sub) sub.textContent = `ENGINEERING INTELLIGENCE OS · v${this.version}`;
        }
      })
      .catch(() => {})
      .finally(done);
  }

  private schedule(fn: () => void, ms: number) {
    this.timers.push(window.setTimeout(fn, ms));
  }

  private typeLine(text: string, cb: () => void) {
    const div = document.createElement("div");
    div.className = "line";
    this.log.appendChild(div);
    requestAnimationFrame(() => {
      const dots = ".".repeat(Math.max(16 - text.length, 3));
      div.innerHTML = `${text}${dots}<span class="ok">OK</span>`;
    });
    this.schedule(cb, 220);
  }

  private runBoot(i: number) {
    if (this.bootSkipped) return;
    if (i >= BOOT_LINES.length) {
      const done = document.createElement("div");
      done.className = "line prompt";
      done.textContent = "System Ready.";
      this.log.appendChild(done);
      this.schedule(() => {
        const launching = document.createElement("div");
        launching.className = "line prompt";
        launching.textContent = "Launching Workspace...";
        this.log.appendChild(launching);
        this.schedule(() => this.finish(), 700);
      }, 400);
      return;
    }
    this.typeLine(BOOT_LINES[i], () => this.runBoot(i + 1));
  }

  private skip() {
    this.timers.forEach((t) => clearTimeout(t));
    this.timers = [];
    this.log.innerHTML = "";
    const done = document.createElement("div");
    done.className = "line prompt";
    done.textContent = "System Ready.";
    this.log.appendChild(done);
    const launching = document.createElement("div");
    launching.className = "line prompt";
    launching.textContent = "Launching Workspace...";
    this.log.appendChild(launching);
    this.schedule(() => this.finish(), 500);
  }

  private finish() {
    document.removeEventListener("keydown", this.onSkip);
    this.el.style.opacity = "0";
    this.el.style.transition = "opacity 0.3s";
    this.schedule(() => {
      this.el.remove();
      this.onComplete();
    }, 300);
  }
}
