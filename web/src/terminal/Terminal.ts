import { api } from "../api/client";

export interface TerminalContext {
  openApp: (id: string) => void;
  logActivity: (text: string) => void;
}

const DEVICE = "esp32_01";

export class Terminal {
  private log: HTMLElement;
  private input: HTMLInputElement;
  private ctx: TerminalContext;

  constructor(termbar: HTMLElement, ctx: TerminalContext) {
    this.ctx = ctx;
    termbar.innerHTML = `<div id="termlog"></div>
      <div id="terminput-row">&gt;<input id="terminput" type="text" autocomplete="off" placeholder="type a command..."/></div>`;
    this.log = termbar.querySelector("#termlog") as HTMLElement;
    this.input = termbar.querySelector("#terminput") as HTMLInputElement;
    this.input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      const val = this.input.value.trim();
      if (!val) return;
      this.print("> " + val, "cmd");
      this.run(val);
      this.input.value = "";
    });
    this.print("PROMETHEUS shell ready. Type 'help' for commands.", "resp");
  }

  print(text: string, cls = "resp") {
    const div = document.createElement("div");
    div.className = cls;
    div.textContent = text;
    this.log.appendChild(div);
    this.log.scrollTop = this.log.scrollHeight;
  }

  private async run(raw: string) {
    const val = raw.toLowerCase();
    if (val.startsWith("open ")) {
      const app = raw.slice(5).trim().toLowerCase();
      this.ctx.openApp(app);
      this.print("opened " + app, "resp");
      return;
    }
    try {
      switch (val) {
        case "help":
          this.print(
            "commands: connect phone, run simulation, show devices, search firmware, recover device, explain kernel, open <app>",
          );
          break;
        case "show devices":
          this.ctx.openApp("devices");
          this.print("opened Devices", "resp");
          break;
        case "connect phone":
          await api.devicesSimulated(DEVICE);
          this.ctx.logActivity("Device Connected");
          this.print(`connecting... ${DEVICE} linked over serial.`, "resp");
          break;
        case "run simulation":
          this.ctx.openApp("simulation");
          this.ctx.logActivity("Simulation Completed");
          await api.simulationRun(DEVICE, "disconnect");
          this.print("scenario queued: phone boot loop", "resp");
          break;
        case "search firmware":
          try {
            const fw: any = await api.gammaFirmware(DEVICE);
            const fmt = fw.format ?? "bin";
            const sha = fw.sha256 ? String(fw.sha256).slice(0, 12) : "verified";
            const segs = fw.segment_count ?? (fw.segments ? fw.segments.length : 3);
            this.print(`firmware match: ${DEVICE}, sha256 ${sha} verified, segment_count=${segs}`, "resp");
          } catch (e: any) {
            this.print(`firmware lookup failed: ${e.message}`, "resp");
          }
          break;
        case "recover device":
          try {
            const plan: any = await api.epsilonRecovery(DEVICE);
            this.print("recovery plan generated — see engineering.recovery_planner.", "resp");
            if (plan && plan.steps) this.print(JSON.stringify(plan.steps), "resp");
          } catch (e: any) {
            this.print(`recovery failed: ${e.message}`, "resp");
          }
          break;
        case "explain kernel":
          this.print("kernel/runtime.py boots config -> plugins -> devices -> agents -> knowledge graph -> scheduler.", "resp");
          try {
            const cs: any = await api.coreStatus();
            this.print(`core status: ${JSON.stringify(cs.status ?? cs)}`, "resp");
          } catch {}
          break;
        default:
          this.print("unrecognized command. type 'help'.", "resp");
      }
    } catch (e: any) {
      this.print("error: " + e.message, "resp");
    }
  }
}
