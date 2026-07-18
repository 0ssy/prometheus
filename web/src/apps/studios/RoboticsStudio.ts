import { createStudioBase } from "./StudioFramework";

export interface RoboticsStudioOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountRoboticsStudio({ container, shell }: RoboticsStudioOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "robotics",
    title: "Robotics Studio",
    icon: "🤖",
    description: "Robot control, simulation, and path planning.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">ROBOT CONTROL</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
      <input id="rb-device" placeholder="robot_id" value="studio-0" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="rb-mode" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="teleop">Teleoperation</option>
        <option value="autonomous">Autonomous</option>
        <option value="simulation">Simulation</option>
      </select>
      <button id="rb-connect" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">Connect</button>
      <button id="rb-run" style="background: var(--border); color: var(--text); border: 1px solid var(--cyan); padding: 4px 10px; cursor: pointer;">Run Task</button>
    </div>
    <div id="rb-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#rb-log") as HTMLElement;
  const deviceInput = content.querySelector("#rb-device") as HTMLInputElement;
  const modeSelect = content.querySelector("#rb-mode") as HTMLSelectElement;
  const connectBtn = content.querySelector("#rb-connect") as HTMLElement;
  const runBtn = content.querySelector("#rb-run") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  connectBtn.addEventListener("click", async () => {
    const deviceId = deviceInput.value.trim() || "studio-0";
    line(`> connecting to robot ${deviceId} (${modeSelect.value})...`, "var(--muted)");
    ui.setStatus("connecting");
    try {
      await new Promise((r) => setTimeout(r, 500));
      line(`connected: ${deviceId}`, "var(--green)");
      ui.setStatus("connected");
      ui.setDirty(true);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  runBtn.addEventListener("click", async () => {
    const deviceId = deviceInput.value.trim() || "studio-0";
    const mode = modeSelect.value;
    line(`> running ${mode} task on ${deviceId}...`, "var(--muted)");
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 800));
      line(`task complete: path planned, joints updated`, "var(--green)");
      ui.setStatus("idle");
      ui.setDirty(false);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("Robotics Studio ready. Select a mode and connect.", "var(--muted)");
  ui.setStatus("ready");
}
