import { api } from "../api/client";
import { store } from "../os/Store";

export function mountKernel(el: HTMLElement) {
  el.innerHTML = `<div id="kernel-app" style="padding: 12px; font-family: var(--font-body); font-size: 16px;"></div>`;
  const header = el.querySelector("#kernel-app") as HTMLElement;
  if (!header) return;
  update();
  store.subscribe(() => update());
  function update() {
    const s = store.state.status;
    if (!s) return;
    const data = (s as any);
    header.innerHTML = `
      <div style="color: var(--text); font-size: 20px; font-family: var(--font-heading); margin-bottom: 12px;">KERNEL</div>
      <div>status: <span id="k-status" style="color: var(--yellow);">${data.kernel ?? "loading"}</span></div>
      <div>version: ${data.version ?? "loading"}</div>
      <div style="margin-top: 12px;">Subsystems</div>
      <pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border);">${JSON.stringify(data.core_status, null, 2)}</pre>
    `;
  }
}
