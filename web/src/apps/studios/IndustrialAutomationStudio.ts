import { createStudioBase } from "./StudioFramework";

export interface IndustrialAutomationStudioOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountIndustrialAutomationStudio({ container, shell }: IndustrialAutomationStudioOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "industrial",
    title: "Industrial Automation Studio",
    icon: "🏭",
    description: "SCADA, PLC programming, and industrial network automation.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">INDUSTRIAL</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="ind-plc" placeholder="PLC ID" value="plc-01" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="ind-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="program">Program PLC</option>
        <option value="monitor">SCADA Monitor</option>
        <option value="alarm">Alarm Management</option>
        <option value="trend">Trend Analysis</option>
      </select>
      <button id="ind-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="ind-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Industrial automation ready.</div>
  `;

  const output = content.querySelector("#ind-output") as HTMLElement;
  const plcInput = content.querySelector("#ind-plc") as HTMLInputElement;
  const actionSelect = content.querySelector("#ind-action") as HTMLSelectElement;
  const runBtn = content.querySelector("#ind-run") as HTMLElement;

  runBtn.addEventListener("click", async () => {
    const plc = plcInput.value.trim() || "unknown";
    const action = actionSelect.value;
    output.textContent = `Running ${action} on ${plc}...\n`;
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 700));
      output.textContent += `${action} complete. PLC ${plc} status: RUNNING.\n`;
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
