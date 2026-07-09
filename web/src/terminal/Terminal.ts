import { api } from "../api/client";
import { store } from "../os/Store";

export interface TerminalState {
  history: string[];
  output: string[];
}

export class Terminal {
  private root: HTMLElement;
  private input: HTMLInputElement;
  private buffer: string[] = [];

  constructor(root: HTMLElement) {
    this.root = root;
    const inputLine = document.createElement("div");
    inputLine.className = "terminal-input-line";
    inputLine.innerHTML = `<span style="color: var(--yellow);">root@prometheus:~$</span>`;
    this.input = document.createElement("input");
    this.input.className = "terminal-input";
    this.input.spellcheck = false;
    this.input.autocomplete = "off";
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const val = this.input.value.trim();
        if (val) {
          this.print(`root@prometheus:~$ ${val}`);
          this.onCommand(val);
          this.input.value = "";
        }
      }
    });
    inputLine.appendChild(this.input);
    this.root.appendChild(inputLine);
    this.root.appendChild(Object.assign(document.createElement("hr"), { style: "border: none; border-top: 1px solid var(--border); margin: 4px 0;" }));
    this.root.appendChild(this.bufferEl());
  }

  print(text: string) {
    const line = document.createElement("div");
    line.textContent = text;
    this.root.insertBefore(line, this.root.lastElementChild!.previousElementSibling!);
    this.root.scrollTop = this.root.scrollHeight;
  }

  printJSON(data: any) {
    this.print(JSON.stringify(data, null, 2));
  }

  private bufferEl() {
    const d = document.createElement("div");
    d.style.flex = "1";
    d.style.overflowY = "auto";
    return d;
  }

  async onCommand(cmd: string) {
    const parts = cmd.split(" ");
    const c = parts[0].toLowerCase();
    try {
      switch (c) {
        case "help": {
          const list = [
            "help",
            "status",
            "devices",
            "agents",
            "kernel",
            "open <app>",
            "clear",
            "assistant <prompt>",
          ];
          this.print(list.join("\n"));
          break;
        }
        case "status": {
          const s = await api.status();
          this.printJSON(s);
          break;
        }
        case "devices": {
          const s = await api.status();
          this.printJSON({ devices: (s as any).devices });
          break;
        }
        case "agents": {
          const s = await api.status();
          this.printJSON({ agents: (s as any).agent_statuses ?? (s as any).agents });
          break;
        }
        case "kernel": {
          const s = await api.status();
          this.printJSON({ kernel: (s as any).kernel });
          break;
        }
        case "open": {
          const target = parts.slice(1).join(" ").toLowerCase();
          if (target) window.dispatchEvent(new CustomEvent("terminal:open", { detail: target }));
          else this.print("Usage: open <app>");
          break;
        }
        case "assistant": {
          const prompt = parts.slice(1).join(" ");
          if (!prompt) { this.print("Usage: assistant <prompt>"); break; }
          const r: any = await api.assistant(prompt);
          this.print(r.response);
          break;
        }
        case "clear":
          this.root.innerHTML = "";
          break;
        default:
          this.print(`Unknown command: ${c}`);
      }
    } catch (e) {
      this.print(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
}
