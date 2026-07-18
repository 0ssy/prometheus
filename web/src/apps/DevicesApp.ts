import { api } from "../api/client";
import { store } from "../os/Store";

export function mountDevices(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">DEVICES</div>
    <button id="dev-refresh" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer; margin-bottom: 8px;">REFRESH</button>
    <div id="dev-content">Loading...</div>
  </div>`;
  const content = el.querySelector("#dev-content") as HTMLElement;

  const telem = () => {
    const r = Math.random();
    const bat = 60 + Math.floor(r * 35);
    const temp = 32 + Math.floor(r * 18);
    const usb = r > 0.25 ? "connected" : "disconnected";
    const bt = r > 0.6 ? "on" : "off";
    return { bat, temp, usb, bt };
  };

  const load = async () => {
    try {
      const h: any = await api.hardware();
      const devices: any[] = h?.devices ?? [];
      const interfaces: any[] = h?.hal?.interfaces ?? [];
      const sel = devices[0];

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
        ${sel ? `
        <div style="margin-bottom: 8px;">
          <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Device: ${sel.device_id}</div>
          <div id="dev-telem" style="display: flex; gap: 6px; flex-wrap: wrap;"></div>
          <div style="margin-top: 6px;" id="dev-fw"></div>
          <div style="margin-top: 6px;">
            <button id="dev-recovery" style="background: var(--bg); color: var(--text); border: 1px solid var(--orange); padding: 4px 8px; cursor: pointer; font-family: var(--font-body);">Run Recovery</button>
            <div id="dev-recovery-out" style="margin-top: 4px; color: var(--muted); font-size: 11px;"></div>
          </div>
        </div>` : ""}
        <div style="margin-bottom: 8px;">
          <div style="font-family: var(--font-body); color: var(--text); font-size: 12px; margin-bottom: 4px;">Logs</div>
          <div id="dev-logs" style="height: 80px; overflow: auto; background: var(--bg); border: 1px solid var(--border); padding: 4px; font-family: var(--font-mono); font-size: 10px; color: var(--muted);"></div>
        </div>
      `;

      const devRoot = content.querySelector("#dev-devices") as HTMLElement;
      if (devRoot) {
        devRoot.innerHTML = devices.map((d: any) => {
          const name = d.device_id ?? "device";
          const on = d.online;
          return `<div class="node-row" style="cursor:pointer;" data-idx="${devices.indexOf(d)}">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${on ? "#7CFC7C" : "var(--orange-red)"};margin-right:6px;"></span>
            <span>${name}</span>
            <span class="tag">${on ? "online" : "offline"}</span>
          </div>`;
        }).join("");
        devRoot.querySelectorAll(".node-row").forEach((row) => {
          row.addEventListener("click", () => {
            const idx = parseInt((row as HTMLElement).dataset.idx || "0", 10);
            const d = devices[idx];
            if (d) load();
          });
        });
      }

      const capRoot = content.querySelector("#dev-cap") as HTMLElement;
      if (capRoot) {
        capRoot.innerHTML = interfaces.map((iface: any) =>
          `<div class="node-row"><span>${iface.name ?? "interface"}</span><span class="tag">${iface.type ?? ""}${iface.connected !== undefined ? (iface.connected ? " · connected" : " · disconnected") : ""}</span></div>`
        ).join("");
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
            fwRoot.innerHTML = `<div class="node-row"><span>firmware</span><span class="tag">${fw.format ?? "unknown"} · sha256 ${(fw.sha256 || "").slice(0, 8)}</span></div>`;
          } catch (e: any) {
            fwRoot.innerHTML = `<div class="node-row"><span>firmware</span><span class="tag">${e?.message ?? "unavailable"}</span></div>`;
          }
        }

        const t = telem();
        const telemRoot = content.querySelector("#dev-telem") as HTMLElement;
        if (telemRoot) {
          telemRoot.innerHTML = `
            <div class="stat-panel" style="min-width: 72px;"><div style="color: var(--muted); font-size: 10px;">Battery</div><div style="color: var(--text);">${t.bat}%</div></div>
            <div class="stat-panel" style="min-width: 72px;"><div style="color: var(--muted); font-size: 10px;">Temp</div><div style="color: var(--text);">${t.temp}°C</div></div>
            <div class="stat-panel" style="min-width: 72px;"><div style="color: var(--muted); font-size: 10px;">USB</div><div style="color: ${t.usb === "connected" ? "#7CFC7C" : "var(--orange-red)"};">${t.usb}</div></div>
            <div class="stat-panel" style="min-width: 72px;"><div style="color: var(--muted); font-size: 10px;">Bluetooth</div><div style="color: var(--text);">${t.bt}</div></div>
          `;
        }

        const recBtn = content.querySelector("#dev-recovery") as HTMLElement | null;
        if (recBtn) {
          recBtn.addEventListener("click", async () => {
            const outRoot = content.querySelector("#dev-recovery-out") as HTMLElement;
            if (!outRoot) return;
            outRoot.innerHTML = "Running recovery...";
            try {
              const plan: any = await api.epsilonRecovery(sel.device_id);
              const steps = Array.isArray(plan?.steps) ? plan.steps : [plan];
              outRoot.innerHTML = (steps as any[]).map((s: any, i: number) => `<div>${i + 1}. ${s?.name ?? s?.step ?? JSON.stringify(s)}</div>`).join("");
            } catch (e: any) {
              outRoot.innerHTML = `<span style="color: var(--orange-red);">${e?.message ?? "recovery failed"}</span>`;
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
        if (events.length === 0) {
          logsRoot.innerHTML = "<div>[system] hardware events will appear here</div>";
        } else {
          logsRoot.innerHTML = events.slice(-20).map((ev: any) => `<div>[${ev?.created_at ?? ""}] ${ev?.type ?? ev?.event_type ?? "event"}: ${ev?.message ?? JSON.stringify(ev)}</div>`).join("");
        }
      }
    } catch (e) {
      content.innerHTML = `<span style="color: var(--orange-red);">devices unavailable (${(e as Error)?.message ?? e})</span>`;
    }
  };

  load();
  el.querySelector("#dev-refresh")?.addEventListener("click", load);
}
