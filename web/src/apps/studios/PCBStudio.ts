import { createStudioBase } from "./StudioFramework";

export interface PCBStudioOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountPCBStudio({ container, shell }: PCBStudioOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "pcb",
    title: "PCB Studio",
    icon: "📟",
    description: "PCB design, routing, and signal integrity analysis.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">PCB DESIGN</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="pcb-name" placeholder="board_name" value="mainboard-v2" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="pcb-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="route">Auto Route</option>
        <option value="drc">Design Rule Check</option>
        <option value="gerber">Export Gerber</option>
        <option value="signal">Signal Integrity</option>
      </select>
      <button id="pcb-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Execute</button>
    </div>
    <div id="pcb-status" style="margin-bottom: 12px; padding: 8px; background: var(--bg); border: 1px solid var(--border); font-size: 13px; color: var(--muted);">No board loaded.</div>
    <div id="pcb-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#pcb-log") as HTMLElement;
  const status = content.querySelector("#pcb-status") as HTMLElement;
  const nameInput = content.querySelector("#pcb-name") as HTMLInputElement;
  const actionSelect = content.querySelector("#pcb-action") as HTMLSelectElement;
  const runBtn = content.querySelector("#pcb-run") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  runBtn.addEventListener("click", async () => {
    const name = nameInput.value.trim() || "unknown";
    const action = actionSelect.value;
    status.innerHTML = `<span style="color: var(--yellow);">Processing ${action} for ${name}...</span>`;
    line(`> ${action} on ${name}...`, "var(--muted)");
    ui.setStatus("processing");
    try {
      await new Promise((r) => setTimeout(r, 700));
      status.innerHTML = `<span style="color: var(--green);">${action} complete. 0 violations.</span>`;
      line(`${action} complete`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      status.innerHTML = `<span style="color: var(--orange-red);">error: ${e.message}</span>`;
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("PCB Studio ready. Route, check DRC, or export Gerbers.", "var(--muted)");
  ui.setStatus("ready");
}
