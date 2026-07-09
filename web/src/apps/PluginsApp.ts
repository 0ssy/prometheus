import { api } from "../api/client";

export function mountPlugins(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">PLUGINS</div>
    <div id="plugins-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#plugins-content") as HTMLElement;
  api.plugins().then((p: any) => {
    const plugins: any[] = p.plugins ?? [];
    if (!plugins.length) {
      content.innerHTML = '<div style="color: var(--muted);">No plugins installed</div>';
      return;
    }
    content.innerHTML = plugins
      .map(
        (plugin) =>
          `<div class="node-row"><span>${plugin.name ?? "unknown"}</span><span class="tag">${plugin.version ?? "v0.1.0"}</span></div>`,
      )
      .join("");
  });
}
