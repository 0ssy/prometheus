const LINES = [
  "PROMETHEUS Engineering Intelligence OS",
  "(c) 2026 Prometheus Labs",
  "",
  "BOOT SEQUENCE INITIATED...",
  "",
  "[  OK  ] Load kernel runtime",
  "[  OK  ] Mount hardware HAL",
  "[  OK  ] Initialize knowledge graph",
  "[  OK  ] Start reasoning pipeline",
  "[  OK  ] Load plugin registry",
  "[  OK  ] Register agent pool",
  "[  OK  ] Warm memory store",
  "[  OK  ] Open event bus",
  "[  OK  ] Bind simulation engine",
  "",
  "ALL SYSTEMS NOMINAL.",
];

export class BootSequence {
  private el: HTMLElement;
  private onComplete: () => void;
  private idx = 0;
  private queue: HTMLElement[] = [];

  constructor(onComplete: () => void) {
    this.el = document.createElement("div");
    this.el.className = "boot-screen";
    this.el.id = "boot-screen";
    this.onComplete = onComplete;
    for (let i = 0; i < LINES.length; i++) {
      const line = document.createElement("div");
      line.style.minHeight = LINES[i] === "" ? "18px" : "auto";
      this.el.appendChild(line);
      this.queue.push(line);
    }
    document.body.appendChild(this.el);
  }

  start() {
    if (this.queue.length === 0) {
      this.finish();
      return;
    }
    const line = this.queue.shift()!;
    const text = LINES[this.idx++];
    if (text.startsWith("[  OK  ]")) {
      line.style.color = "var(--text)";
      line.textContent = text;
    } else if (text === "") {
      line.textContent = "";
    } else {
      line.style.color = "var(--yellow)";
      line.textContent = text;
    }
    setTimeout(() => this.start(), 60 + Math.random() * 80);
  }

  private finish() {
    setTimeout(() => {
      this.el.style.opacity = "0";
      this.el.style.transition = "opacity 0.4s";
      setTimeout(() => {
        this.el.remove();
        this.onComplete();
      }, 400);
    }, 300);
  }
}
