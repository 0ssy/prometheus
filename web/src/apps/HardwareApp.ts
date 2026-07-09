import { api } from "../api/client";

export function mountHardware(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">HARDWARE</div>
    <div id="hw-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#hw-content") as HTMLElement;
  api.hardware().then((h: any) => {
    content.innerHTML = `<pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border);">${JSON.stringify(h, null, 2)}</pre>`;
  });
}
