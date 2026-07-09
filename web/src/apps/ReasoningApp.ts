import { api } from "../api/client";

export function mountReasoning(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">REASONING</div>
    <div id="reasoning-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#reasoning-content") as HTMLElement;
  Promise.all([api.capabilities(), api.observability()]).then(([caps, obs]: any[]) => {
    const rows: string[] = [];
    rows.push(`<div class="node-row"><span>Pipeline</span><span class="tag">active</span></div>`);
    if (obs && obs.last_recommendation) {
      rows.push(`<div class="node-row"><span>Last recommendation</span><span class="tag">${obs.last_recommendation}</span></div>`);
    }
    rows.push(`<div class="node-row"><span>Risk</span><span class="tag">${obs?.risk ?? "low"}</span></div>`);
    rows.push(`<div class="node-row"><span>Capabilities</span><span class="tag">${caps?.length ?? 0}</span></div>`);
    content.innerHTML = rows.join("");
  }).catch((e: any) => {
    content.innerHTML = `<span style="color: var(--orange-red);">${e.message}</span>`;
  });
}
