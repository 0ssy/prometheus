import { api } from "../api/client";

const ACTIVE = /(thinking|running|learning|active|busy)/i;

export function mountAgents(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">AGENTS</div>
    <div id="agents-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#agents-content") as HTMLElement;
  api.agents().then((a: any) => {
    const agents: any[] = a.agents ?? [];
    if (!agents.length) {
      content.innerHTML = '<div style="color: var(--muted);">No agents registered</div>';
      return;
    }
    content.innerHTML = agents
      .map((agent) => {
        const status: string = (agent.status ?? "idle").toString();
        const cls = status.toLowerCase().replace(/[^a-z]/g, "") || "idle";
        const active = ACTIVE.test(status) ? " active" : "";
        const bar = ACTIVE.test(status)
          ? `<div class="bar-track"><div class="bar-fill anim" style="width:${50 + Math.floor(Math.random() * 45)}%"></div></div>`
          : "";
        return `<div class="agent-row">
          <div class="name"><span class="status-dot ${cls === "active" ? "running" : cls}"></span>${agent.name}</div>
          <div class="state${active}">${status}</div>
          ${bar}
        </div>`;
      })
      .join("");
  });
}
