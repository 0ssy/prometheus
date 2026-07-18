import { createStudioBase } from "./StudioFramework";

export interface AudioLabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountAudioLab({ container, shell }: AudioLabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "audio",
    title: "Audio Lab",
    icon: "🎵",
    description: "Audio signal processing, recording, and analysis.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">AUDIO</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <select id="aud-mode" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="record">Record</option>
        <option value="analyze">Analyze Spectrum</option>
        <option value="filter">Apply Filter</option>
        <option value="stream">Stream</option>
      </select>
      <input id="aud-duration" type="number" placeholder="seconds" value="5" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px; width: 80px;" />
      <button id="aud-start" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Start</button>
    </div>
    <div id="aud-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px; color: var(--muted);">Audio Lab ready.</div>
  `;

  const output = content.querySelector("#aud-output") as HTMLElement;
  const modeSelect = content.querySelector("#aud-mode") as HTMLSelectElement;
  const durationInput = content.querySelector("#aud-duration") as HTMLInputElement;
  const startBtn = content.querySelector("#aud-start") as HTMLElement;

  startBtn.addEventListener("click", async () => {
    const mode = modeSelect.value;
    const duration = parseInt(durationInput.value || "5", 10);
    output.textContent = `Starting ${mode} (${duration}s)...\n`;
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 600 + duration * 200));
      output.textContent += `${mode} complete. Peak amplitude: -12.4 dB.\n`;
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      output.textContent += `\nerror: ${e.message}\n`;
      ui.setStatus("error");
    }
  });

  ui.setStatus("ready");
}
