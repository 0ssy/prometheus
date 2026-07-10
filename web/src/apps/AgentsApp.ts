import { api } from "../api/client";

const STATUS_LABEL: Record<string, string> = {
  thinking: "Thinking...",
  running: "Running",
  learning: "Learning",
  waiting: "Waiting",
  idle: "Idle",
  active: "Active",
  busy: "Busy",
};

const STATUS_DOT_COLOR: Record<string, string> = {
  thinking: "var(--yellow)",
  running: "var(--orange)",
  learning: "var(--purple)",
  idle: "var(--steel)",
  waiting: "var(--steel)",
  active: "var(--yellow)",
  busy: "var(--orange-red)",
};

const hasBar = (s: string) => ["thinking", "running", "learning"].includes(s);

function renderAgents(agents: any[]) {
  if (!agents.length) {
    return '<div style="color: var(--muted);">No agents registered</div>';
  }
  return agents
    .map((agent: any) => {
      const raw: string = (agent.status ?? "idle").toString();
      const status = raw.toLowerCase();
      const label = STATUS_LABEL[status] ?? "Idle";
      const dotColor = STATUS_DOT_COLOR[status] ?? "var(--muted)";
      const dotClass = ["thinking", "running", "learning", "idle"].includes(status)
        ? `status-dot ${status}`
        : "status-dot";
      const bar = hasBar(status)
        ? `<div class="bar-track"><div class="bar-fill anim" style="width:${50 + Math.floor(Math.random() * 45)}%"></div></div>`
        : "";
      const waiting = status === "waiting"
        ? `<div class="bar-track"><div class="bar-fill anim" style="width:30%;opacity:.4"></div></div>`
        : "";
      const hasKnownClass = ["thinking", "running", "learning", "idle"].includes(status);
      const dotStyle = hasKnownClass ? "" : `style="background:${dotColor}"`;
      return `<div class="agent-row">
        <div class="name"><span class="status-dot ${hasKnownClass ? status : ""}" ${dotStyle}></span>${agent.name}</div>
        <div class="state${hasBar(status) || status === "waiting" ? " active" : ""}">${label}</div>
        ${bar}${waiting}
      </div>`;
    })
    .join("");
}

export function mountAgents(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">AGENTS</div>
    <div id="agents-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#agents-content") as HTMLElement;

  const update = async () => {
    try {
      const a: any = await api.agents();
      content.innerHTML = renderAgents(a.agents ?? []);
    } catch {
      content.innerHTML = '<div style="color: var(--muted);">Error loading agents</div>';
    }
  };

  update();
  const id = setInterval(update, 2000);
  window.addEventListener("beforeunload", () => clearInterval(id));
}
