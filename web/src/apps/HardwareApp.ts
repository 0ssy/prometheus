import { api } from "../api/client";

export function mountHardware(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">HARDWARE</div>
    <div id="hw-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#hw-content") as HTMLElement;
  api.hardware().then((h: any) => {
    const devices: any[] = h?.devices ?? [];
    if (devices.length === 0) {
      content.innerHTML = '<div class="node-row"><span>no hardware</span><span class="tag">offline</span></div>';
      return;
    }
    content.innerHTML = devices
      .map((d) => {
        const name = d.device_id ?? d.id ?? "device";
        const status = d.online ? "online" : "offline";
        const meta = [d.interface, d.platform, d.firmware].filter(Boolean).join(" · ");
        return `<div class="node-row"><span>${name}</span><span class="tag">${meta || status}</span></div>`;
      })
      .join("");
  });
}
