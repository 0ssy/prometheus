import { api } from "../api/client";

export function mountSimulation(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">SIMULATION</div>
    <select id="sim-device" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 4px; font-family: var(--font-body);">
      <option value="">-- device --</option>
      <option value="sim-1">sim-1</option>
      <option value="sim-2">sim-2</option>
    </select>
    <select id="sim-mode" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 4px; font-family: var(--font-body);">
      <option value="disconnect">disconnect</option>
      <option value="latency_spike">latency_spike</option>
      <option value="write_failure">write_failure</option>
    </select>
    <button id="sim-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer;">RUN</button>
    <div id="sim-out" style="margin-top: 12px;"></div>
  </div>`;
  const out = el.querySelector("#sim-out") as HTMLElement;
  el.querySelector("#sim-run")?.addEventListener("click", async () => {
    const device_id = (el.querySelector("#sim-device") as HTMLSelectElement).value;
    const failure_mode = (el.querySelector("#sim-mode") as HTMLSelectElement).value;
    if (!device_id) { out.innerHTML = '<span style="color: var(--orange-red);">Select a device</span>'; return; }
    out.innerHTML = '<span style="color: var(--muted);">Running...</span>';
    try {
      const res: any = await api.simulationRun(device_id, failure_mode);
      out.innerHTML = `<pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border); white-space: pre-wrap;">${JSON.stringify(res, null, 2)}</pre>`;
    } catch (e: any) {
      out.innerHTML = `<span style="color: var(--orange-red);">${e.message}</span>`;
    }
  });
}
