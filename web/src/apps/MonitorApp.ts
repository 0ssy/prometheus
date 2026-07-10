import { api } from "../api/client";
import { store } from "../os/Store";

export function mountMonitor(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px; font-family: var(--font-body); font-size: 12px; color: var(--text);">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">SYSTEM MONITOR</div>
    <div id="mon-resources"></div>
    <div id="mon-observability" style="margin-top: 8px;"></div>
    <div id="mon-jobs" style="margin-top: 8px;"></div>
    <div id="mon-workflows" style="margin-top: 8px;"></div>
  </div>`;

  const resourcesEl = el.querySelector("#mon-resources") as HTMLElement;
  const observabilityEl = el.querySelector("#mon-observability") as HTMLElement;
  const jobsEl = el.querySelector("#mon-jobs") as HTMLElement;
  const workflowsEl = el.querySelector("#mon-workflows") as HTMLElement;

  const fmt = (v: number, d: number = 1) => `${v.toFixed(d)}`;
  const bar = (used: number, limit: number, color: string) => {
    const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
    return `<div style="display:flex;align-items:center;gap:6px;"><span style="width:70px;">${fmt(used)}</span><div style="flex:1;height:8px;background:var(--border);border-radius:1px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${color};"></div></div><span style="width:50px;text-align:right;color:var(--muted);">/${fmt(limit, 0)}</span></div>`;
  };

  const renderResources = (r: any) => {
    const cpuColor = r.cpu_percent > 80 ? "var(--orange-red)" : r.cpu_percent > 50 ? "var(--orange)" : "#7CFC7C";
    const memColor = r.memory_mb > (r.limits?.max_memory_mb || 4096) * 0.8 ? "var(--orange-red)" : "#7CFC7C";
    resourcesEl.innerHTML = `
      <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">RESOURCES</div>
      <div style="margin-bottom: 4px;">CPU ${bar(r.cpu_percent, 100, cpuColor)}</div>
      <div style="margin-bottom: 4px;">Memory ${bar(r.memory_mb, r.limits?.max_memory_mb || 4096, memColor)}</div>
      <div style="margin-bottom: 4px;">Disk ${bar(r.disk_mb, r.limits?.max_disk_mb || 10240, "#7CFC7C")}</div>
      <div style="margin-bottom: 4px;">Network ${bar(r.network_mbps, 1000, "#7CFC7C")}</div>
      <div style="margin-bottom: 4px;">Connections <span class="tag">${r.active_connections}</span></div>
      ${r.throttled ? `<div style="color: var(--orange-red);">Throttled: ${r.throttle_reason || "unknown"}</div>` : ""}
      ${r.psutil_unavailable ? `<div style="color: var(--muted);">psutil not available — live metrics disabled</div>` : ""}
    `;
  };

  const renderObservability = (o: any) => {
    const subs = o.subsystems || {};
    const rows = Object.entries(subs).map(([k, v]) => `<div class="node-row"><span>${k}</span><span class="tag">${v}</span></div>`).join("");
    observabilityEl.innerHTML = `
      <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">OBSERVABILITY</div>
      <div class="node-row"><span>Events/sec</span><span class="tag">${o.events_per_sec ?? 0}</span></div>
      <div class="node-row"><span>Commands/sec</span><span class="tag">${o.commands_per_sec ?? 0}</span></div>
      <div style="margin-top: 4px; font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">SUBSYSTEMS</div>
      ${rows || '<div style="color: var(--muted);">loading...</div>'}
    `;
  };

  const renderJobs = (data: any) => {
    const jobs: any[] = data?.jobs || [];
    const rows = jobs.map((j: any) => {
      const color = j.status === "failed" ? "var(--orange-red)" : j.status === "running" ? "var(--yellow)" : j.status === "paused" ? "var(--muted)" : "var(--text)";
      return `<div class="node-row"><span>${j.name}</span><span class="tag" style="color:${color}">${j.status}</span><span style="color:var(--muted);margin-left:8px;">fails:${j.failures}</span></div>`;
    }).join("");
    jobsEl.innerHTML = `
      <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">JOBS</div>
      ${rows || '<div style="color: var(--muted);">no jobs</div>'}
    `;
  };

  const renderWorkflows = (data: any) => {
    const wfs: any[] = data?.workflows || [];
    const rows = wfs.map((w: any) => {
      const color = w.status === "completed" ? "#7CFC7C" : w.status === "failed" ? "var(--orange-red)" : w.status === "running" ? "var(--yellow)" : "var(--muted)";
      const stepCount = (w.steps || []).length;
      const doneCount = (w.steps || []).filter((s: any) => s.status === "done").length;
      return `<div class="node-row"><span>${w.name}</span><span class="tag" style="color:${color}">${w.status}</span><span style="color:var(--muted);margin-left:8px;">${doneCount}/${stepCount}</span></div>`;
    }).join("");
    workflowsEl.innerHTML = `
      <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 11px; margin-bottom: 4px;">WORKFLOWS</div>
      ${rows || '<div style="color: var(--muted);">no workflows</div>'}
    `;
  };

  const render = async () => {
    try {
      const [resources, observability, jobs, workflows] = await Promise.all([
        api.systemResources().catch(() => ({})),
        api.observability().catch(() => ({})),
        api.systemJobs().catch(() => ({})),
        api.workflows().catch(() => ({})),
      ]);
      renderResources(resources);
      renderObservability(observability);
      renderJobs(jobs);
      renderWorkflows(workflows);
    } catch (e) {
      resourcesEl.innerHTML = `<span style="color: var(--orange-red);">monitor unavailable</span>`;
    }
  };

  render().catch(() => {});
  let intervalId: number | null = null;
  intervalId = window.setInterval(render, 2000);
  el.addEventListener("disconnect", () => { if (intervalId !== null) clearInterval(intervalId); });
}
