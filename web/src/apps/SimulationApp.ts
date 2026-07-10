import { api } from "../api/client";
import { store } from "../os/Store";

export function mountSimulation(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">SIMULATION</div>
    <div id="sim-root">
      <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px;">
        <select id="sim-device" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 4px; font-family: var(--font-body);">
          <option value="">-- device --</option>
          <option value="esp32_01">esp32_01</option>
          <option value="twin_demo">twin_demo</option>
        </select>
        <select id="sim-mode" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 4px; font-family: var(--font-body);">
          <option value="disconnect">disconnect</option>
          <option value="latency_spike">latency_spike</option>
          <option value="write_failure">write_failure</option>
        </select>
        <button id="sim-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; font-family: var(--font-body);">RUN</button>
      </div>
      <div id="sim-out" style="margin-bottom: 12px; font-size: 14px; color: var(--muted);"></div>
      <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Digital Twin</div>
      <div id="sim-twin" style="margin-bottom: 8px;"></div>
      <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Runs</div>
      <div id="sim-runs" style="margin-bottom: 8px;"></div>
    </div>
  </div>`;
  const out = el.querySelector("#sim-out") as HTMLElement;
  const runsEl = el.querySelector("#sim-runs") as HTMLElement;
  const twinEl = el.querySelector("#sim-twin") as HTMLElement;
  let intervalId: number | null = null;
  let lastRunResult: any = null;

  const confidenceColor = (c: any) => {
    const n = typeof c === "string" ? parseFloat(c) : Number(c || 0);
    if (n >= 0.6) return "var(--yellow)";
    if (n >= 0.3) return "var(--orange)";
    return "var(--orange-red)";
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "running": return "var(--yellow)";
      case "complete": return "var(--green)";
      case "failed": return "var(--orange-red)";
      default: return "var(--muted)";
    }
  };

  const render = async () => {
    try {
      const list: any = await api.simulationList();
      const runs: any[] = list?.runs ?? [];
      if (twinEl) {
        const withResult = runs.find((r: any) => r?.result_json);
        if (withResult) {
          let result: any = null;
          try { result = JSON.parse(withResult.result_json); } catch { result = null; }
          const state = result?.state ?? result?.status ?? "unknown";
          const health = result?.health ?? result?.overall_health ?? "n/a";
          twinEl.innerHTML = `<div class="node-row"><span>twin state</span><span class="tag">${String(state)}</span></div>
            <div class="node-row"><span>health</span><span class="tag">${String(health)}</span></div>`;
        } else {
          twinEl.innerHTML = '<div style="color: var(--muted); font-size: 11px;">no digital twin data yet</div>';
        }
      }

      if (runsEl) {
        runsEl.innerHTML = runs.map((r: any) => {
          const id = r?.id ?? r?.run_id ?? "run";
          const px = typeof r?.progress === "number" ? r.progress + "%" : (String(r?.progress || "0%"));
          const isAnim = r?.status === "running" ? "anim" : "";
          let rec = "—";
          try {
            const parsed = JSON.parse(r?.result_json || "{}");
            rec = parsed?.recommendation ?? parsed?.next_step ?? rec;
          } catch { /* leave rec */ }
          return `<div class="agent-row">
            <div class="name">${r?.device_id ?? "?"} · ${r?.failure_mode ?? "n/a"}</div>
            <div class="bar-track"><div class="bar-fill ${isAnim}" style="width:${px}"></div></div>
            <div class="state" style="color: ${statusColor(r?.status ?? "")};">${r?.status ?? "idle"}${r?.status === "running" ? " · live" : ""}</div>
            <div style="color: var(--muted); font-size: 11px; min-width: 90px;">risk: ${r?.risk ?? "—"}</div>
            <div style="color: ${confidenceColor(r?.confidence)}; font-size: 11px; min-width: 90px;">conf: ${r?.confidence ?? "—"}</div>
            <div style="color: var(--muted); font-size: 11px; min-width: 120px;">rec: ${rec}</div>
          </div>`;
        }).join("");
      }
    } catch (e) {
      if (runsEl) runsEl.innerHTML = `<span style="color: var(--orange-red);">simulation unavailable (${(e as Error)?.message ?? e})</span>`;
    }
  };

  render();
  intervalId = window.setInterval(render, 3000);

  el.querySelector("#sim-run")?.addEventListener("click", async () => {
    const device_id = (el.querySelector("#sim-device") as HTMLSelectElement).value;
    const failure_mode = (el.querySelector("#sim-mode") as HTMLSelectElement).value;
    if (!device_id) {
      out.innerHTML = '<span style="color: var(--orange-red);">Select a device</span>';
      return;
    }
    out.innerHTML = '<span style="color: var(--muted);">Running...</span>';
    try {
      const res: any = await api.simulationRun(device_id, failure_mode);
      lastRunResult = res;
      out.innerHTML = `<pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border); white-space: pre-wrap;">${JSON.stringify(res, null, 2)}</pre>`;
    } catch (e: any) {
      out.innerHTML = `<span style="color: var(--orange-red);">${e.message}</span>`;
    }
  });
}
