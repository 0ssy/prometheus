import { api } from "../api/client";

/**
 * P11 Prometheus OS — unified engineering workspace / AI OS experience.
 *
 * Composes the platform's subsystems into one single-page OS view:
 * kernel health, observability subsystems, and resource utilization.
 * Talks to the existing /health, /observability, /system/resources
 * endpoints (Python + SQL + Rust backend).
 */
export function mountOS(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px; font-family: var(--font-body); font-size: 12px; color: var(--text);">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">PROMETHEUS OS</div>
    <div id="os-kernel"></div>
    <div id="os-subsystems" style="margin-top: 8px;"></div>
    <div id="os-resources" style="margin-top: 8px;"></div>
  </div>`;

  const kernelEl = el.querySelector("#os-kernel") as HTMLElement;
  const subsEl = el.querySelector("#os-subsystems") as HTMLElement;
  const resEl = el.querySelector("#os-resources") as HTMLElement;

  const render = async () => {
    try {
      const [health, obs, res] = await Promise.all([
        api.health().catch(() => ({}) as any),
        api.observability().catch(() => ({}) as any),
        api.systemResources().catch(() => ({}) as any),
      ]);
      kernelEl.innerHTML = `<div class="node-row"><span>Kernel</span><span class="tag" style="color:${health.status === "ok" ? "#7CFC7C" : "var(--orange-red)"}">${health.status ?? "n/a"}</span></div>`;
      const subs = obs.subsystems ?? {};
      subsEl.innerHTML = `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">SUBSYSTEMS</div>` +
        (Object.keys(subs).length
          ? Object.entries(subs).map(([k, v]) => `<div class="node-row"><span>${k}</span><span class="tag">${v}</span></div>`).join("")
          : '<div style="color: var(--muted);">loading...</div>');
      resEl.innerHTML = `<div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">RESOURCES</div>` +
        `<div class="node-row"><span>CPU</span><span class="tag">${res.cpu_percent ?? "n/a"}%</span></div>` +
        `<div class="node-row"><span>Memory</span><span class="tag">${res.memory_mb ?? "n/a"} MB</span></div>`;
    } catch (e: any) {
      kernelEl.innerHTML = `<span style="color: var(--orange-red);">OS shell unavailable</span>`;
    }
  };

  render().catch(() => {});
  const id = window.setInterval(render, 3000);
  el.addEventListener("disconnect", () => clearInterval(id));
}
