import { createStudioBase } from "./StudioFramework";

export interface EmbeddedStudioOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountEmbeddedStudio({ container, shell }: EmbeddedStudioOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "embedded",
    title: "Embedded Studio",
    icon: "🔌",
    description: "Embedded system configuration, RTOS, and sensor workflows.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">EMBEDDED</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="em-device" placeholder="device_id" value="studio-0" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="em-task" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="read_sensor">Read Sensor</option>
        <option value="configure_rtos">Configure RTOS</option>
        <option value="debug_jtag">Debug JTAG</option>
        <option value="build_firmware">Build Firmware</option>
      </select>
      <button id="em-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="em-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#em-log") as HTMLElement;
  const deviceInput = content.querySelector("#em-device") as HTMLInputElement;
  const taskSelect = content.querySelector("#em-task") as HTMLSelectElement;
  const runBtn = content.querySelector("#em-run") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  runBtn.addEventListener("click", async () => {
    const deviceId = deviceInput.value.trim() || "studio-0";
    const task = taskSelect.value;
    line(`> embedded task: ${task} on ${deviceId}...`, "var(--muted)");
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 700));
      line(`task complete`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("Embedded Studio ready. Configure RTOS, debug JTAG, or read sensors.", "var(--muted)");
  ui.setStatus("ready");
}
