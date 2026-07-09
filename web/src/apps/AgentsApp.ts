import { api } from "../api/client";

export function mountAgents(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">AGENTS</div>
    <div id="agents-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#agents-content") as HTMLElement;
  api.agents().then((a: any) => {
    if (!a.agents || a.agents.length === 0) {
      content.innerHTML = "<div style='color: var(--muted);'>No agents registered</div>";
      return;
    }
    const list = document.createElement("div");
    list.style.display = "flex";
    list.style.flexDirection = "column";
    list.style.gap = "6px";
    for (const agent of a.agents) {
      const card = document.createElement("div");
      card.style.cssText = "border: 1px solid var(--border); padding: 8px; background: var(--bg);";
      const dotClass = agent.status || "idle";
      card.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span class="status-dot ${dotClass}"></span>
          <span style="font-family: var(--font-heading); font-size: 10px; color: var(--text);">${agent.name}</span>
          <span style="color: var(--muted); font-size: 14px;">status: ${agent.status}</span>
        </div>
        ${agent.last_task ? `<div style="color: var(--muted); font-size: 12px; margin-top: 4px;">last: ${JSON.stringify(agent.last_task)}</div>` : ''}
        ${agent.updated_at ? `<div style="color: var(--muted); font-size: 12px;">updated: ${agent.updated_at}</div>` : ''}
      `;
      list.appendChild(card);
    }
    content.innerHTML = "";
    content.appendChild(list);
  });
}
