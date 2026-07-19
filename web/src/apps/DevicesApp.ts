import { api } from "../api/client";
import { store } from "../os/Store";

function esc(str: unknown): string {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function mountDevices(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">DEVICES</div>
    <button id="dev-refresh" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; margin-bottom: 8px;">REFRESH</button>
    <div id="dev-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#dev-content") as HTMLElement;

  let selectedDeviceId: string | null = null;

  const telem = () => {
    const r = Math.random();
    const bat = 60 + Math.floor(r * 35);
    const temp = 32 + Math.floor(r * 18);
    const usb = r > 0.25 ? "connected" : "disconnected";
    const bt = r > 0.6 ? "on" : "off";
    return { bat, temp, usb, bt };
  };

  const load = async (deviceId?: string) => {
    try {
      const h: any = await api.hardware();
      const devices: any[] = h?.devices ?? [];
      const interfaces: any[] = h?.hal?.interfaces ?? [];
      selectedDeviceId = deviceId ?? devices[0]?.device_id ?? null;
      const sel = devices.find((d: any) => d.device_id === selectedDeviceId) ?? devices[0];

      content.innerHTML = `
        <div style="margin-bottom: 8px;">
          <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Connected devices</div>
          <div id="dev-devices"></div>
        </div>
        <div style="margin-bottom: 8px;">
          <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Capabilities</div>
          <div id="dev-cap"></div>
        </div>
        <div style="margin-bottom: 8px;">
          <button id="dev-demo" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; font-family: var(--font-body);">Connect demo device</button>
        </div>
        <div style="margin-bottom: 8px;">
          <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Logs</div>
          <div id="dev-logs" style="height: 80px; overflow: auto; background: var(--bg); border: 1px solid var(--border); padding: 4px; font-family: var(--font-mono); font-size: 10px; color: var(--muted);"></div>
        </div>
      `;

      const devRoot = content.querySelector("#dev-devices") as HTMLElement;
      if (devRoot) {
        const frag = document.createDocumentFragment();
        devices.forEach((d: any, idx: number) => {
          const row = document.createElement("div");
          row.className = "node-row";
          row.style.cssText = "cursor:pointer;";
          row.dataset.idx = String(idx);

          const dot = document.createElement("span");
          dot.style.cssText = "display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;";
          dot.style.background = d.online ? "#7CFC7C" : "var(--orange-red)";

          const name = document.createElement("span");
          name.textContent = d.device_id ?? "device";

          const tag = document.createElement("span");
          tag.className = "tag";
          tag.textContent = d.online ? "online" : "offline";

          row.appendChild(dot);
          row.appendChild(name);
          row.appendChild(tag);
          frag.appendChild(row);

          row.addEventListener("click", () => {
            const clickedId = devices[idx]?.device_id;
            if (clickedId) load(clickedId);
          });
        });
        devRoot.appendChild(frag);
      }

      const capRoot = content.querySelector("#dev-cap") as HTMLElement;
      if (capRoot) {
        const frag = document.createDocumentFragment();
        interfaces.forEach((iface: any) => {
          const row = document.createElement("div");
          row.className = "node-row";

          const nameSpan = document.createElement("span");
          nameSpan.textContent = iface.name ?? "interface";

          const tag = document.createElement("span");
          tag.className = "tag";
          const type = esc(iface.type ?? "");
          const conn = iface.connected !== undefined ? (iface.connected ? " · connected" : " · disconnected") : "";
          tag.textContent = type + conn;

          row.appendChild(nameSpan);
          row.appendChild(tag);
          frag.appendChild(row);
        });
        capRoot.appendChild(frag);
      }

      const demoBtn = content.querySelector("#dev-demo") as HTMLElement | null;
      if (demoBtn) {
        demoBtn.addEventListener("click", async () => {
          try {
            await api.devicesSimulated("esp32_01");
            await api.declareOwnership("esp32_01", "demo device");
            load();
          } catch (e: any) {
            alert(e?.message || "failed to register demo device");
          }
        });
      }

      if (sel) {
        const fwRoot = content.querySelector("#dev-fw") as HTMLElement;
        if (fwRoot) {
          try {
            const fw: any = await api.gammaFirmware(sel.device_id);
            const fwRow = document.createElement("div");
            fwRow.className = "node-row";

            const fwSpan = document.createElement("span");
            fwSpan.textContent = "firmware";

            const fwTag = document.createElement("span");
            fwTag.className = "tag";
            const fmt = esc(fw.format ?? "unknown");
            const sha = esc((fw.sha256 || "").slice(0, 8));
            fwTag.textContent = `${fmt} · sha256 ${sha}`;

            fwRow.appendChild(fwSpan);
            fwRow.appendChild(fwTag);
            fwRoot.innerHTML = "";
            fwRoot.appendChild(fwRow);
          } catch (e: any) {
            const fwRow = document.createElement("div");
            fwRow.className = "node-row";

            const fwSpan = document.createElement("span");
            fwSpan.textContent = "firmware";

            const fwTag = document.createElement("span");
            fwTag.className = "tag";
            fwTag.textContent = esc(e?.message ?? "unavailable");

            fwRow.appendChild(fwSpan);
            fwRow.appendChild(fwTag);
            fwRoot.innerHTML = "";
            fwRoot.appendChild(fwRow);
          }
        }

        const t = telem();
        const telemRoot = content.querySelector("#dev-telem") as HTMLElement;
        if (telemRoot) {
          const frag = document.createDocumentFragment();
          const stats = [
            { label: "Battery", value: `${t.bat}%`, color: "var(--text)" },
            { label: "Temp", value: `${t.temp}°C`, color: "var(--text)" },
            { label: "USB", value: t.usb, color: t.usb === "connected" ? "#7CFC7C" : "var(--orange-red)" },
            { label: "Bluetooth", value: t.bt, color: "var(--text)" },
          ];
          stats.forEach((s) => {
            const panel = document.createElement("div");
            panel.className = "stat-panel";
            panel.style.cssText = "min-width: 72px;";
            const lbl = document.createElement("div");
            lbl.style.cssText = "color: var(--muted); font-size: 10px;";
            lbl.textContent = s.label;
            const val = document.createElement("div");
            val.style.cssText = `color: ${s.color};`;
            val.textContent = s.value;
            panel.appendChild(lbl);
            panel.appendChild(val);
            frag.appendChild(panel);
          });
          telemRoot.innerHTML = "";
          telemRoot.appendChild(frag);
        }

        const recBtn = content.querySelector("#dev-recovery") as HTMLElement | null;
        if (recBtn) {
          recBtn.addEventListener("click", async () => {
            const outRoot = content.querySelector("#dev-recovery-out") as HTMLElement;
            if (!outRoot) return;
            outRoot.textContent = "Running recovery...";
            try {
              const plan: any = await api.epsilonRecovery(sel.device_id);
              const steps = Array.isArray(plan?.steps) ? plan.steps : [plan];
              const frag = document.createDocumentFragment();
              (steps as any[]).forEach((s: any, i: number) => {
                const div = document.createElement("div");
                const idx = document.createElement("span");
                idx.textContent = `${i + 1}. `;
                const name = document.createElement("span");
                name.textContent = s?.name ?? s?.step ?? JSON.stringify(s);
                div.appendChild(idx);
                div.appendChild(name);
                frag.appendChild(div);
              });
              outRoot.innerHTML = "";
              outRoot.appendChild(frag);
            } catch (e: any) {
              const span = document.createElement("span");
              span.style.cssText = "color: var(--orange-red);";
              span.textContent = esc(e?.message ?? "recovery failed");
              outRoot.innerHTML = "";
              outRoot.appendChild(span);
            }
          });
        }
      }

      const logsRoot = content.querySelector("#dev-logs") as HTMLElement;
      if (logsRoot) {
        const st: any = store.state as any;
        const events: any[] = (st?.events ?? []).filter((ev: any) => {
          const t = (ev?.type || ev?.event_type || "").toString().toLowerCase();
          return t.includes("device") || t.includes("hardware");
        });
        const frag = document.createDocumentFragment();
        if (events.length === 0) {
          const div = document.createElement("div");
          div.textContent = "[system] hardware events will appear here";
          frag.appendChild(div);
        } else {
          events.slice(-20).forEach((ev: any) => {
            const div = document.createElement("div");
            const ts = esc(ev?.created_at ?? "");
            const type = esc(ev?.type ?? ev?.event_type ?? "event");
            const msg = esc(ev?.message ?? JSON.stringify(ev));
            div.textContent = `[${ts}] ${type}: ${msg}`;
            frag.appendChild(div);
          });
        }
        logsRoot.innerHTML = "";
        logsRoot.appendChild(frag);
      }
    } catch (e) {
      content.innerHTML = "";
      const span = document.createElement("span");
      span.style.cssText = "color: var(--orange-red);";
      span.textContent = `devices unavailable (${esc((e as Error)?.message ?? e)})`;
      content.appendChild(span);
    }
  };

  load();
  el.querySelector("#dev-refresh")?.addEventListener("click", () => load(selectedDeviceId ?? undefined));
}
