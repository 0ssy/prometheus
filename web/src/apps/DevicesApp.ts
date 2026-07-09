import { api } from "../api/client";

export function mountDevices(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">DEVICES</div>
    <button id="dev-refresh" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; margin-bottom: 8px;">REFRESH</button>
    <div id="dev-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#dev-content") as HTMLElement;
  const load = () =>
    api.devices().then((d: any) => {
      const devices: any[] = Array.isArray(d) ? d : d?.devices ?? d?.declared ?? [];
      if (!devices.length) {
        content.innerHTML = '<div class="node-row"><span>no devices</span><span class="tag">declared</span></div>';
        return;
      }
      content.innerHTML = devices
        .map((dev) => {
          const name = dev.device_id ?? dev.id ?? "device";
          const owner = dev.owner ?? dev.declared_owner ?? "Joseph";
          const trust = dev.trust ?? (dev.ownership_declared ? "declared" : "unverified");
          return `<div class="node-row"><span>${name}</span><span class="tag">owner: ${owner}</span></div>
            <div class="node-row"><span>trust</span><span class="tag">${trust}</span></div>`;
        })
        .join("");
    });
  load();
  el.querySelector("#dev-refresh")?.addEventListener("click", load);
}
