import { createStudioBase } from "./StudioFramework";

export interface IoTLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountIoTLab({ container, shell }: IoTLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "iot",
    title: "IoT Lab",
    icon: "📡",
    description: "IoT device management, provisioning, and telemetry.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">IOT</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="iot-device" placeholder="device_id" value="sensor-01" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="iot-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="provision">Provision</option>
        <option value="telemetry">Stream Telemetry</option>
        <option value="ota">OTA Update</option>
        <option value="inventory">Inventory</option>
      </select>
      <button id="iot-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="iot-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#iot-log") as HTMLElement;
  const deviceInput = content.querySelector("#iot-device") as HTMLInputElement;
  const actionSelect = content.querySelector("#iot-action") as HTMLSelectElement;
  const runBtn = content.querySelector("#iot-run") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  runBtn.addEventListener("click", async () => {
    const device = deviceInput.value.trim() || "unknown";
    const action = actionSelect.value;
    line(`> ${action} for ${device}...`, "var(--muted)");
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 600));
      line(`${action} complete. Device ${device} updated.`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("IoT Lab ready. Provision devices or stream telemetry.", "var(--muted)");
  ui.setStatus("ready");
}
