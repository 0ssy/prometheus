import { api } from "../api/client";

export function mountSettings(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">SETTINGS</div>
    <div id="settings-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#settings-content") as HTMLElement;
  Promise.all([api.health(), api.status()]).then(([health, status]: any[]) => {
    const rows = [
      "Models",
      "Plugins",
      "Hardware",
      "Security",
      "Permissions",
    ];
    const list = rows.map((r) => `<div class="node-row"><span>${r}</span><span class="tag">›</span></div>`).join("");
    const v = health?.version ?? status?.version ?? "0.6.0-omega";
    content.innerHTML = `<div class="node-row"><span>Version</span><span class="tag">${v}</span></div>${list}`;
  });
}
