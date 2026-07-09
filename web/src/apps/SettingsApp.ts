import { api } from "../api/client";

export function mountSettings(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">SETTINGS</div>
    <div id="settings-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#settings-content") as HTMLElement;
  Promise.all([api.health(), api.status()]).then(([health, status]) => {
    content.innerHTML = `<pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border); white-space: pre-wrap;">${JSON.stringify({ health, status }, null, 2)}</pre>`;
  });
}
