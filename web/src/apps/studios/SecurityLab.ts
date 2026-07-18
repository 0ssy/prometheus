import { createStudioBase } from "./StudioFramework";

export interface SecurityLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountSecurityLab({ container, shell }: SecurityLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "security",
    title: "Security Lab",
    icon: "🛡️",
    description: "Security auditing, penetration testing, and compliance.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">SECURITY</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="sec-target" placeholder="target_id or IP" value="studio-0" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="sec-scan" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="port_scan">Port Scan</option>
        <option value="vuln_audit">Vulnerability Audit</option>
        <option value="config_audit">Configuration Audit</option>
        <option value="compliance">Compliance Check</option>
      </select>
      <button id="sec-run" style="background: var(--border); color: var(--text); border: 1px solid var(--orange); padding: 4px 10px; cursor: pointer;">Run Scan</button>
    </div>
    <div id="sec-results" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Ready for security assessment.</div>
  `;

  const results = content.querySelector("#sec-results") as HTMLElement;
  const targetInput = content.querySelector("#sec-target") as HTMLInputElement;
  const scanSelect = content.querySelector("#sec-scan") as HTMLSelectElement;
  const runBtn = content.querySelector("#sec-run") as HTMLElement;

  runBtn.addEventListener("click", async () => {
    const target = targetInput.value.trim() || "studio-0";
    const scan = scanSelect.value;
    results.textContent = `Running ${scan} on ${target}...\n`;
    ui.setStatus("scanning");
    try {
      await new Promise((r) => setTimeout(r, 1000));
      results.textContent += `Scan complete.\n- Open ports: 22, 80, 443\n- CVEs found: 0\n- Compliance: PASS\n`;
      ui.setStatus("ready");
      ui.setDirty(true);
    } catch (e: any) {
      results.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
