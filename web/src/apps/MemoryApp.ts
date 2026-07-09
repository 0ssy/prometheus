import { api } from "../api/client";

export function mountMemory(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">MEMORY</div>
    <button id="mem-refresh" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer;">REFRESH</button>
    <pre id="mem-content" style="background: var(--bg); padding: 8px; border: 1px solid var(--border); margin-top: 8px;"></pre>
  </div>`;
  const content = el.querySelector("#mem-content") as HTMLElement;
  function load() { api.memory().then((m: any) => { content.textContent = JSON.stringify(m, null, 2); }); }
  load();
  el.querySelector("#mem-refresh")?.addEventListener("click", load);
}
