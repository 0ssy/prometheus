import { store } from "../os/Store";

export function mountKernel(el: HTMLElement) {
  el.innerHTML = `<div id="kernel-app" style="padding: 4px;"></div>`;
  const root = el.querySelector("#kernel-app") as HTMLElement;
  if (!root) return;
  const render = () => {
    const s = (store.state.status || {}) as any;
    const core = s.core_status || {};
    root.innerHTML = `
      <div class="node-row"><span>Runtime</span><span class="tag">${s.kernel ?? "unknown"}</span></div>
      <div class="node-row"><span>Uptime</span><span class="tag" id="k-uptime">--:--:--</span></div>
      <div class="node-row"><span>Scheduler</span><span class="tag">${core.status ?? "idle"}</span></div>
      <div class="node-row"><span>Bootstrap</span><span class="tag">core/bootstrap.py</span></div>`;
    const up = root.querySelector("#k-uptime");
    if (up) {
      window.setInterval(() => {
        up.textContent = new Date().toLocaleTimeString("en-GB");
      }, 1000);
    }
  };
  render();
  store.subscribe(render);
}
