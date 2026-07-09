import { api } from "../api/client";

export function mountPlugins(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">PLUGINS</div>
    <div id="plugins-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#plugins-content") as HTMLElement;
  api.plugins().then((p: any) => {
    if (!p.plugins || p.plugins.length === 0) {
      content.innerHTML = "<div style='color: var(--muted);'>No plugins installed</div>";
      return;
    }
    const list = document.createElement("div");
    list.style.display = "flex";
    list.style.flexDirection = "column";
    list.style.gap = "6px";
    for (const plugin of p.plugins) {
      const card = document.createElement("div");
      card.style.cssText = "border: 1px solid var(--border); padding: 8px; background: var(--bg);";
      card.innerHTML = `<div style="font-family: var(--font-heading); font-size: 10px; color: var(--text);">${plugin.name ?? "unknown"}</div>
        <div style="color: var(--muted); font-size: 14px;">${plugin.description ?? ""}</div>`;
      list.appendChild(card);
    }
    content.innerHTML = "";
    content.appendChild(list);
  });
}
