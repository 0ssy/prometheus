import { api } from "../api/client";

export function mountMemory(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">MEMORY</div>
    <button id="mem-refresh" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; margin-bottom: 8px;">REFRESH</button>
    <div id="mem-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#mem-content") as HTMLElement;
  const load = () =>
    api.memory().then((m: any) => {
      const entries = m?.entries ?? m?.long_term ?? [];
      const count = Array.isArray(entries) ? entries.length : m?.count ?? 0;
      const lastTag = m?.last_tag ?? (m?.tags && m.tags[0]) ?? "milestone";
      content.innerHTML = `
        <div class="node-row"><span>Long-term entries</span><span class="tag">${count}</span></div>
        <div class="node-row"><span>Last tag</span><span class="tag">${lastTag}</span></div>`;
    });
  load();
  el.querySelector("#mem-refresh")?.addEventListener("click", load);
}
