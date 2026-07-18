import { createStudioBase } from "./StudioFramework";

export interface VisionLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountVisionLab({ container, shell }: VisionLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "vision",
    title: "Vision Lab",
    icon: "👁️",
    description: "Computer vision pipelines, SLAM, and image analysis.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">COMPUTER VISION</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <select id="vis-pipeline" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="object_detect">Object Detection</option>
        <option value="slam">SLAM</option>
        <option value="segmentation">Segmentation</option>
        <option value="optical_flow">Optical Flow</option>
      </select>
      <button id="vis-start" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Start Pipeline</button>
      <button id="vis-stop" style="background: var(--border); color: var(--text); border: 1px solid var(--border); padding: 4px 10px; cursor: pointer;">Stop</button>
    </div>
    <div id="vis-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Vision pipeline idle.</div>
  `;

  const output = content.querySelector("#vis-output") as HTMLElement;
  const pipelineSelect = content.querySelector("#vis-pipeline") as HTMLSelectElement;
  const startBtn = content.querySelector("#vis-start") as HTMLElement;
  const stopBtn = content.querySelector("#vis-stop") as HTMLElement;

  startBtn.addEventListener("click", async () => {
    const pipeline = pipelineSelect.value;
    output.textContent = `Starting ${pipeline} pipeline...\n`;
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 600));
      output.textContent += `Pipeline active. FPS: 30, detections: 12 objects.\n`;
      ui.setStatus("running");
      ui.setDirty(true);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  stopBtn.addEventListener("click", () => {
    output.textContent += "Pipeline stopped.\n";
    ui.setStatus("ready");
    ui.setDirty(false);
  });

  ui.setStatus("ready");
}
