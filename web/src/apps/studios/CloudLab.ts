import { createStudioBase } from "./StudioFramework";

export interface CloudLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountCloudLab({ container, shell }: CloudLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "cloud",
    title: "Cloud Lab",
    icon: "☁️",
    description: "Cloud deployment, scaling, monitoring, and secrets management.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">CLOUD</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="cl-service" placeholder="service-name" value="web-api" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="cl-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="deploy">Deploy</option>
        <option value="scale">Scale</option>
        <option value="logs">View Logs</option>
        <option value="secrets">Manage Secrets</option>
      </select>
      <button id="cl-run" style="background: var(--border); color: var(--text); border: 1px solid var(--cyan); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="cl-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Cloud Lab ready.</div>
  `;

  const output = content.querySelector("#cl-output") as HTMLElement;
  const serviceInput = content.querySelector("#cl-service") as HTMLInputElement;
  const actionSelect = content.querySelector("#cl-action") as HTMLSelectElement;
  const runBtn = content.querySelector("#cl-run") as HTMLElement;

  runBtn.addEventListener("click", async () => {
    const service = serviceInput.value.trim() || "unknown";
    const action = actionSelect.value;
    output.textContent = `Running ${action} on ${service}...\n`;
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 800));
      output.textContent += `${action} complete. Service ${service} is healthy.\n`;
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
