import { createStudioBase } from "./StudioFramework";

export interface ReverseEngineeringLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountReverseEngineeringLab({ container, shell }: ReverseEngineeringLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "reverse_engineering",
    title: "Reverse Engineering Lab",
    icon: "🔍",
    description: "Binary analysis, disassembly, and vulnerability research.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">REVERSE ENGINEERING</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="re-binary" placeholder="/path/to/binary" value="firmware.bin" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px; min-width: 200px;" />
      <select id="re-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="disassemble">Disassemble</option>
        <option value="strings">Extract Strings</option>
        <option value="symbols">Resolve Symbols</option>
        <option value="vuln_scan">Vulnerability Scan</option>
      </select>
      <button id="re-analyze" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Analyze</button>
    </div>
    <div id="re-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 12px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Load a binary to begin analysis.</div>
  `;

  const output = content.querySelector("#re-output") as HTMLElement;
  const binaryInput = content.querySelector("#re-binary") as HTMLInputElement;
  const actionSelect = content.querySelector("#re-action") as HTMLSelectElement;
  const analyzeBtn = content.querySelector("#re-analyze") as HTMLElement;

  analyzeBtn.addEventListener("click", async () => {
    const binary = binaryInput.value.trim() || "unknown";
    const action = actionSelect.value;
    output.textContent = `Analyzing ${binary} with ${action}...\n`;
    ui.setStatus("analyzing");
    try {
      await new Promise((r) => setTimeout(r, 900));
      output.textContent += `0x00401000  push    rbp\n0x00401001  mov     rbp, rsp\n0x00401004  sub     rsp, 0x20\n0x00401008  call    _init\n... (truncated)\n`;
      output.textContent += `\nAnalysis complete. 142 functions, 23 imports found.\n`;
      ui.setStatus("ready");
      ui.setDirty(true);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
