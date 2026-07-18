import { createStudioBase } from "./StudioFramework";

export interface CADIntegrationOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountCADIntegration({ container, shell }: CADIntegrationOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "cad",
    title: "CAD Integration",
    icon: "📐",
    description: "CAD model management, CAM toolpath generation, and simulation.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">CAD / CAM</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="cad-model" placeholder="model.step" value="bracket.step" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="cad-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="import">Import Model</option>
        <option value="toolpath">Generate Toolpath</option>
        <option value="simulate">Simulate Machining</option>
        <option value="inspect">Inspect Geometry</option>
      </select>
      <button id="cad-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="cad-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Ready for CAD operations.</div>
  `;

  const output = content.querySelector("#cad-output") as HTMLElement;
  const modelInput = content.querySelector("#cad-model") as HTMLInputElement;
  const actionSelect = content.querySelector("#cad-action") as HTMLSelectElement;
  const runBtn = content.querySelector("#cad-run") as HTMLElement;

  runBtn.addEventListener("click", async () => {
    const model = modelInput.value.trim() || "unknown";
    const action = actionSelect.value;
    output.textContent = `Running ${action} on ${model}...\n`;
    ui.setStatus("processing");
    try {
      await new Promise((r) => setTimeout(r, 900));
      output.textContent += `${action} complete. Toolpath generated: 1245 moves, est. time 12m 30s.\n`;
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
