import { sdk } from "../sdk";

const HARDWARE_CAPABILITIES: { name: string; permissions: string[]; mutating: boolean }[] = [
  { name: "hardware.connect", permissions: ["device.connect"], mutating: true },
  { name: "hardware.disconnect", permissions: ["device.disconnect"], mutating: true },
  { name: "hardware.read", permissions: ["device.read"], mutating: false },
  { name: "hardware.write", permissions: ["device.write"], mutating: true },
  { name: "hardware.diagnose", permissions: ["device.diagnose"], mutating: false },
  { name: "hardware.simulate", permissions: ["device.simulate"], mutating: false },
  { name: "hardware.verify", permissions: ["device.read"], mutating: false },
  { name: "hardware.flash", permissions: ["device.flash", "ownership_declared"], mutating: true },
  { name: "hardware.recover", permissions: ["device.recover", "ownership_declared"], mutating: true },
  { name: "hardware.reboot", permissions: ["device.reboot", "ownership_declared"], mutating: true },
];

const ENGINEERING_MODULES = [
  "firmware", "boot_chain", "partition", "recovery", "crypto",
  "embedded", "robotics", "mechanical", "electrical",
  "networking", "cybersecurity", "ai", "data", "cloud",
];

const MODULE_WORKFLOWS: Record<string, string[]> = {
  embedded: ["flash_firmware", "read_sensor", "configure_rtos", "debug_jtag", "build_firmware"],
  robotics: ["run_slam", "plan_path", "control_motor", "capture_vision", "simulate_physics"],
  mechanical: ["analyze_stress", "run_motion_simulation", "generate_cam_toolpath", "check_materials"],
  electrical: ["simulate_circuit", "analyze_power", "capture_oscilloscope", "route_pcb", "check_signal_integrity"],
  networking: ["capture_packets", "analyze_topology", "diagnose_connectivity", "scan_ports", "monitor_bandwidth"],
  cybersecurity: ["scan_vulnerabilities", "audit_configuration", "analyze_logs", "verify_compliance", "check_patch_status"],
  ai: ["manage_model", "run_prompt", "evaluate_model", "fine_tune", "run_inference", "build_rag_index"],
  data: ["query_database", "run_etl", "build_knowledge_graph", "analyze_vector_store", "export_dataset"],
  cloud: ["deploy_container", "scale_service", "check_health", "pull_logs", "manage_secrets"],
};

const TITAN_WORKFLOWS: Record<string, string[]> = {
  dataset_builder: ["prepare", "pipeline", "get"],
  tokenizer: ["encode", "decode", "add_special_tokens"],
  finetune: ["submit", "get", "list", "run"],
  evaluation: ["benchmark", "pipeline", "grade"],
  quantization: ["quantize", "convert"],
  registry: ["register", "get", "list", "version", "tag", "deploy", "register_as_provider"],
  experiments: ["start", "log_metrics", "log_checkpoint", "complete", "compare", "list"],
};

export function mountEngineeringStudio(el: HTMLElement) {
  const capOptions = HARDWARE_CAPABILITIES.map(
    (c) =>
      `<option value="${c.name}">${c.name}${c.mutating ? " (write)" : ""}</option>`,
  ).join("");

  const modOptions = ENGINEERING_MODULES.map((m) => `<option value="${m}">${m}</option>`).join("");

  el.innerHTML = `<div style="padding: 4px; display: flex; flex-direction: column; height: 100%; box-sizing: border-box;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">ENGINEERING STUDIO</div>
    <div style="color: var(--muted); font-size: 13px; margin-bottom: 8px;">
      Hardware capabilities + engineering workflows. Simulation first, always.
    </div>
    <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; align-items: center;">
      <input id="es-device" placeholder="device_id" value="studio-0"
        style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;" />
      <select id="es-mode" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="hardware">Hardware</option>
        <option value="engineering">Engineering</option>
        <option value="titan">Titan AI</option>
      </select>
      <select id="es-cap" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">${capOptions}</select>
      <select id="es-module" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px; display: none;">${modOptions}</select>
      <select id="es-workflow" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px; display: none;"></select>
      <select id="es-titan-module" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px; display: none;">
        <option value="dataset_builder">Dataset Builder</option>
        <option value="tokenizer">Tokenizer</option>
        <option value="finetune">Fine-Tune</option>
        <option value="evaluation">Evaluation</option>
        <option value="quantization">Quantization</option>
        <option value="registry">Model Registry</option>
        <option value="experiments">Experiments</option>
      </select>
      <select id="es-titan-workflow" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px; display: none;"></select>
      <label style="color: var(--muted); font-size: 13px; display: flex; align-items: center; gap: 4px;">
        <input id="es-owns" type="checkbox" /> ownership_declared
      </label>
    </div>
    <div style="display: flex; gap: 8px; margin-bottom: 8px;">
      <button id="es-sim" style="background: var(--border); color: var(--text); border: 1px solid var(--border); padding: 4px 10px; cursor: pointer;">SIMULATE</button>
      <button id="es-run" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 10px; cursor: pointer;">EXECUTE</button>
      <button id="es-workflow" style="background: var(--border); color: var(--text); border: 1px solid var(--cyan); padding: 4px 10px; cursor: pointer;">RUN WORKFLOW</button>
    </div>
    <div id="es-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px;"></div>
  </div>`;

  const deviceInput = el.querySelector("#es-device") as HTMLInputElement;
  const modeSelect = el.querySelector("#es-mode") as HTMLSelectElement;
  const capSelect = el.querySelector("#es-cap") as HTMLSelectElement;
  const modSelect = el.querySelector("#es-module") as HTMLSelectElement;
  const workflowSelect = el.querySelector("#es-workflow") as HTMLSelectElement;
  const titanModSelect = el.querySelector("#es-titan-module") as HTMLSelectElement;
  const titanWorkflowSelect = el.querySelector("#es-titan-workflow") as HTMLSelectElement;
  const ownsBox = el.querySelector("#es-owns") as HTMLInputElement;
  const log = el.querySelector("#es-log") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  function updateWorkflows() {
    const mod = modSelect.value;
    const workflows = MODULE_WORKFLOWS[mod] || [];
    workflowSelect.innerHTML = workflows.map((w) => `<option value="${w}">${w}</option>`).join("");
    workflowSelect.style.display = workflows.length > 0 ? "inline-block" : "none";
  }

  modSelect.addEventListener("change", updateWorkflows);
  modeSelect.addEventListener("change", () => {
    const isEng = modeSelect.value === "engineering";
    const isTitan = modeSelect.value === "titan";
    capSelect.style.display = isEng || isTitan ? "none" : "inline-block";
    modSelect.style.display = isEng ? "inline-block" : "none";
    workflowSelect.style.display = isEng ? "inline-block" : "none";
    titanModSelect.style.display = isTitan ? "inline-block" : "none";
    titanWorkflowSelect.style.display = isTitan ? "inline-block" : "none";
    if (isTitan) updateTitanWorkflows();
  });

  function updateTitanWorkflows() {
    const mod = titanModSelect.value;
    const workflows = TITAN_WORKFLOWS[mod] || [];
    titanWorkflowSelect.innerHTML = workflows.map((w) => `<option value="${w}">${w}</option>`).join("");
    titanWorkflowSelect.style.display = workflows.length > 0 ? "inline-block" : "none";
  }

  titanModSelect.addEventListener("change", updateTitanWorkflows);

  function permissionsFor(capName: string): string[] {
    const def = HARDWARE_CAPABILITIES.find((c) => c.name === capName);
    const base = def ? [...def.permissions] : [];
    if (ownsBox.checked && !base.includes("ownership_declared")) {
      base.push("ownership_declared");
    }
    return base;
  }

  async function dispatchHardware(capName: string, payload: Record<string, unknown>, simulate: boolean) {
    const permissions = permissionsFor(capName);
    line(`> ${simulate ? "simulate" : "execute"} ${capName} (perms: ${permissions.join(",") || "-"})`, "var(--muted)");
    try {
      const res = await sdk.commands.run({
        capability: capName,
        payload,
        granted_permissions: permissions,
        simulate,
      });
      if ((res as any).ok) {
        line("ok: " + JSON.stringify((res as any).data ?? null), "var(--green)");
      } else {
        line("denied: " + ((res as any).error ?? "unknown"), "var(--red)");
      }
    } catch (e: any) {
      line("error: " + e.message, "var(--red)");
    }
  }

  async function dispatchEngineering(moduleName: string, workflow: string, payload: Record<string, unknown>) {
    line(`> engineering ${moduleName}.${workflow}`, "var(--muted)");
    try {
      const res = await sdk.commands.run({
        module_name: moduleName,
        workflow,
        payload,
      });
      if ((res as any).ok) {
        line("ok: " + JSON.stringify((res as any).data ?? null), "var(--green)");
      } else {
        line("error: " + ((res as any).error ?? "unknown"), "var(--red)");
      }
    } catch (e: any) {
      line("error: " + e.message, "var(--red)");
    }
  }

  async function dispatchTitan(moduleName: string, workflow: string, payload: Record<string, unknown>) {
    line(`> titan ${moduleName}.${workflow}`, "var(--muted)");
    try {
      const res = await sdk.commands.run({
        module_name: moduleName,
        workflow,
        payload,
        titan: true,
      });
      if ((res as any).ok) {
        line("ok: " + JSON.stringify((res as any).data ?? null), "var(--green)");
      } else {
        line("error: " + ((res as any).error ?? "unknown"), "var(--red)");
      }
    } catch (e: any) {
      line("error: " + e.message, "var(--red)");
    }
  }

  async function runWorkflow() {
    const deviceId = deviceInput.value.trim() || "studio-0";
    line("=== cross-discipline workflow: connect → diagnose → verify → disconnect ===", "var(--cyan)");
    await dispatchHardware("hardware.connect", { device_id: deviceId, driver_name: "virtual" }, false);
    await dispatchHardware("hardware.diagnose", { device_id: deviceId }, false);
    await dispatchHardware("hardware.verify", { device_id: deviceId }, false);
    await dispatchHardware("hardware.disconnect", { device_id: deviceId }, false);
  }

  (el.querySelector("#es-sim") as HTMLButtonElement).addEventListener("click", () => {
    if (modeSelect.value === "titan") {
      dispatchTitan(titanModSelect.value, titanWorkflowSelect.value, {});
    } else if (modeSelect.value === "engineering") {
      dispatchEngineering(modSelect.value, workflowSelect.value, {});
    } else {
      dispatchHardware(capSelect.value, { device_id: deviceInput.value.trim() || "studio-0" }, true);
    }
  });
  (el.querySelector("#es-run") as HTMLButtonElement).addEventListener("click", () => {
    if (modeSelect.value === "titan") {
      dispatchTitan(titanModSelect.value, titanWorkflowSelect.value, {});
    } else if (modeSelect.value === "engineering") {
      dispatchEngineering(modSelect.value, workflowSelect.value, {});
    } else {
      dispatchHardware(capSelect.value, { device_id: deviceInput.value.trim() || "studio-0" }, false);
    }
  });
  (el.querySelector("#es-workflow") as HTMLButtonElement).addEventListener("click", runWorkflow);
}
