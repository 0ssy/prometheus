import { api } from "../api/client";

/**
 * P8 Cloud Platform — status & incident dashboard.
 *
 * Shows platform health/uptime and a derived incident list. Talks to the
 * existing /health and /status endpoints (Python + SQL backend).
 */
export function mountStatus(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px; font-family: var(--font-body); font-size: 12px; color: var(--text);">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">PLATFORM STATUS</div>
    <div id="st-health"></div>
    <div id="st-incidents" style="margin-top: 8px;"></div>
  </div>`;

  const healthEl = el.querySelector("#st-health") as HTMLElement;
  const incidentsEl = el.querySelector("#st-incidents") as HTMLElement;

  const render = async () => {
    try {
      const [health, status] = await Promise.all([
        api.health().catch(() => ({})),
        api.status().catch(() => ({})),
      ]);
      const up = health && health.status === "ok";
      const uptime = (status as any).uptime_seconds ?? (status as any).uptime ?? "n/a";
      healthEl.innerHTML = `
        <div class="node-row"><span>Status</span><span class="tag" style="color:${up ? "#7CFC7C" : "var(--orange-red)"}">${up ? "OPERATIONAL" : "DEGRADED"}</span></div>
        <div class="node-row"><span>Version</span><span class="tag">${health?.version ?? "n/a"}</span></div>
        <div class="node-row"><span>Uptime</span><span class="tag">${uptime}s</span></div>
        <div class="node-row"><span>Plugins</span><span class="tag">${(health?.plugins_loaded ?? []).length}</span></div>
        <div class="node-row"><span>Agents</span><span class="tag">${(health?.agents_loaded ?? []).length}</span></div>
      `;
      const incidents = deriveIncidents(health, status);
      incidentsEl.innerHTML = `
        <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">INCIDENTS</div>
        ${incidents.length ? incidents.map((i) => `<div class="node-row"><span>${i.sev}</span><span class="tag" style="color:var(--orange-red)">${i.msg}</span></div>`).join("") : '<div style="color: var(--muted);">no active incidents</div>'}
      `;
    } catch (e: any) {
      healthEl.innerHTML = `<span style="color: var(--orange-red);">status unavailable</span>`;
    }
  };

  render().catch(() => {});
  const id = window.setInterval(render, 5000);
  el.addEventListener("disconnect", () => clearInterval(id));
}

function deriveIncidents(health: any, status: any): { sev: string; msg: string }[] {
  const out: { sev: string; msg: string }[] = [];
  if (!health || health.status !== "ok") out.push({ sev: "P1", msg: "health endpoint not ok" });
  const kernel = status?.kernel;
  if (kernel && kernel !== "ok" && kernel !== "Running") out.push({ sev: "P2", msg: `kernel ${kernel}` });
  return out;
}
