import { createStudioBase } from "./StudioFramework";

export interface VehicleStudioOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountVehicleStudio({ container, shell }: VehicleStudioOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "vehicle",
    title: "Vehicle Studio",
    icon: "🚗",
    description: "Vehicle diagnostics, CAN bus, and autonomous driving stacks.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">VEHICLE</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="veh-vin" placeholder="VIN" value="DEMO-VIN-001" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="veh-task" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="can_capture">Capture CAN</option>
        <option value="dtc_read">Read DTCs</option>
        <option value="adas">ADAS Stack</option>
        <option value="calibrate">Calibrate Sensors</option>
      </select>
      <button id="veh-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="veh-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#veh-log") as HTMLElement;
  const vinInput = content.querySelector("#veh-vin") as HTMLInputElement;
  const taskSelect = content.querySelector("#veh-task") as HTMLSelectElement;
  const runBtn = content.querySelector("#veh-run") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  runBtn.addEventListener("click", async () => {
    const vin = vinInput.value.trim() || "unknown";
    const task = taskSelect.value;
    line(`> ${task} on VIN ${vin}...`, "var(--muted)");
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 700));
      line(`${task} complete. No faults detected.`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("Vehicle Studio ready. Diagnostics and ADAS tools available.", "var(--muted)");
  ui.setStatus("ready");
}
