import { api } from "../api/client";
import { store } from "../os/Store";

export function mountSimulation(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">SIMULATION</div>
    <div id="sim-rows" style="margin-bottom: 12px;"></div>
    <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
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
      <button id="sim-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer;">RUN</button>
    </div>
    <div id="sim-out" style="margin-top: 10px; font-size: 14px; color: var(--muted);"></div>
  </div>`;
  const rows = el.querySelector("#sim-rows") as HTMLElement;
  const out = el.querySelector("#sim-out") as HTMLElement;

  const render = () => {
    const s = (store.state.status || {}) as any;
    rows.innerHTML = `
      <div class="agent-row">
        <div class="name">Scenario: phone boot loop</div>
        <div class="bar-track"><div class="bar-fill anim" style="width:60%"></div></div>
        <div class="state active">running — confidence 0.74</div>
      </div>
      <div class="agent-row">
        <div class="name">Scenario: USB failure</div>
        <div class="bar-track"><div class="bar-fill" style="width:100%"></div></div>
        <div class="state">complete — recovery rate 91%</div>
      </div>
      <div class="node-row"><span>Engine</span><span class="tag">${s.simulation ?? "idle"}</span></div>`;
  };
  render();
  store.subscribe(render);

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
      out.innerHTML = `<pre style="background: var(--bg); padding: 8px; border: 1px solid var(--border); white-space: pre-wrap;">${JSON.stringify(res, null, 2)}</pre>`;
    } catch (e: any) {
      out.innerHTML = `<span style="color: var(--orange-red);">${e.message}</span>`;
    }
  });
}
