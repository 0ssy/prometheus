import { api } from "../api/client";

export function mountReasoning(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">REASONING PIPELINE</div>
    <div id="reasoning-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#reasoning-content") as HTMLElement;
  api.capabilities().then((c: any) => {
    content.innerHTML = `<pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border);">${JSON.stringify(c, null, 2)}</pre>`;
  });
}
