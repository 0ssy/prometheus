import { createStudioBase } from "./StudioFramework";

export interface NetworkingLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountNetworkingLab({ container, shell }: NetworkingLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "networking",
    title: "Networking Lab",
    icon: "🌐",
    description: "Network topology, packet analysis, and connectivity diagnostics.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">NETWORKING</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="net-interface" placeholder="interface" value="eth0" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="net-tool" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="capture">Packet Capture</option>
        <option value="topology">Topology Map</option>
        <option value="diagnose">Connectivity Diagnostics</option>
        <option value="port_scan">Port Scan</option>
      </select>
      <button id="net-run" style="background: var(--border); color: var(--text); border: 1px solid var(--cyan); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="net-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Ready for network analysis.</div>
  `;

  const output = content.querySelector("#net-output") as HTMLElement;
  const ifaceInput = content.querySelector("#net-interface") as HTMLInputElement;
  const toolSelect = content.querySelector("#net-tool") as HTMLSelectElement;
  const runBtn = content.querySelector("#net-run") as HTMLElement;

  runBtn.addEventListener("click", async () => {
    const iface = ifaceInput.value.trim() || "eth0";
    const tool = toolSelect.value;
    output.textContent = `Running ${tool} on ${iface}...\n`;
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 800));
      output.textContent += `Result: ${tool} complete. Traffic observed: 1.2 MB/s, 342 packets.\n`;
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
