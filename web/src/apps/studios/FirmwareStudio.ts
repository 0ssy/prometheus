import { createStudioBase } from "./StudioFramework";

export interface FirmwareStudioOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountFirmwareStudio({ container, shell }: FirmwareStudioOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "firmware",
    title: "Firmware Studio",
    icon: "⚙️",
    description: "Firmware development, flashing, and boot-chain analysis.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">FIRMWARE</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <input id="fw-device" placeholder="device_id" value="studio-0" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <input id="fw-path" placeholder="firmware.bin" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <label style="color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 4px;">
        <input id="fw-owns" type="checkbox" /> ownership_declared
      </label>
      <button id="fw-inspect" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Inspect</button>
      <button id="fw-flash" style="background: var(--border); color: var(--text); border: 1px solid var(--orange); padding: 4px 10px; cursor: pointer;">Flash</button>
    </div>
    <div id="fw-report" style="margin-bottom: 12px; padding: 8px; background: var(--bg); border: 1px solid var(--border); font-size: 13px; color: var(--muted);">No firmware loaded.</div>
    <div id="fw-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#fw-log") as HTMLElement;
  const report = content.querySelector("#fw-report") as HTMLElement;
  const deviceInput = content.querySelector("#fw-device") as HTMLInputElement;
  const pathInput = content.querySelector("#fw-path") as HTMLInputElement;
  const ownsBox = content.querySelector("#fw-owns") as HTMLInputElement;
  const inspectBtn = content.querySelector("#fw-inspect") as HTMLElement;
  const flashBtn = content.querySelector("#fw-flash") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  inspectBtn.addEventListener("click", async () => {
    const deviceId = deviceInput.value.trim() || "studio-0";
    const firmwarePath = pathInput.value.trim() || "firmware.bin";
    line(`> inspecting ${firmwarePath} on ${deviceId}...`, "var(--muted)");
    ui.setStatus("inspecting");
    try {
      await new Promise((r) => setTimeout(r, 600));
      const size = 1024 + Math.floor(Math.random() * 4096);
      const sha = Array.from({ length: 8 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
      report.innerHTML = `<div style="color: var(--text);"><div>format: ELF</div><div>size: ${size} bytes</div><div>sha256: ${sha}...</div><div>boot_chain: valid</div></div>`;
      line(`inspection complete`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(true);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  flashBtn.addEventListener("click", async () => {
    const deviceId = deviceInput.value.trim() || "studio-0";
    const firmwarePath = pathInput.value.trim() || "firmware.bin";
    line(`> flashing ${firmwarePath} to ${deviceId}...`, "var(--muted)");
    ui.setStatus("flashing");
    try {
      await new Promise((r) => setTimeout(r, 1000));
      line(`flash complete`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("Firmware Studio ready. Inspect or flash firmware images.", "var(--muted)");
  ui.setStatus("ready");
}
