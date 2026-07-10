import { api } from "../api/client";

export function mountWorkflow(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">WORKFLOWS</div>
    <div id="wf-form" style="margin-bottom: 8px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
      <input id="wf-name" placeholder="Workflow name" style="background:var(--bg);color:var(--text);border:1px solid var(--border);padding:4px 8px;font-family:var(--font-body);font-size:12px;width:160px;" />
      <input id="wf-steps" placeholder="Steps (comma-separated)" style="background:var(--bg);color:var(--text);border:1px solid var(--border);padding:4px 8px;font-family:var(--font-body);font-size:12px;width:220px;" />
      <button id="wf-create" style="background:var(--border);color:var(--text);border:1px solid var(--yellow);padding:4px 8px;cursor:pointer;font-family:var(--font-body);">New</button>
    </div>
    <div id="wf-content"></div>
  </div>`;
  const formEl = el.querySelector("#wf-form") as HTMLElement;
  const contentEl = el.querySelector("#wf-content") as HTMLElement;

  const stepColor = (s: any) => {
    if (s.status === "done") return "#7CFC7C";
    if (s.status === "failed") return "var(--orange-red)";
    if (s.status === "running") return "var(--yellow)";
    return "var(--muted)";
  };

  const renderWorkflow = (w: any) => {
    const steps = (w.steps || []).map((s: any) => {
      const arrow = `<div style="color:var(--muted);margin:0 4px;">→</div>`;
      return `<div style="display:inline-flex;align-items:center;padding:4px 8px;border:1px solid ${stepColor(s)};border-radius:2px;background:var(--bg);">
        <div style="width:8px;height:8px;border-radius:50%;background:${stepColor(s)};margin-right:6px;"></div>
        <span style="font-size:11px;">${s.description}</span>
      </div>${arrow}`;
    }).join("");
    return `<div class="node-row" style="flex-wrap:wrap;gap:4px;margin-bottom:6px;">
      <span style="flex:1;font-weight:bold;">${w.name}</span>
      <span class="tag" style="color:${w.status === "completed" ? "#7CFC7C" : w.status === "failed" ? "var(--orange-red)" : "var(--yellow)"}">${w.status}</span>
      <button data-run="${w.id}" style="background:var(--border);color:var(--text);border:1px solid var(--yellow);padding:2px 6px;cursor:pointer;font-family:var(--font-body);font-size:10px;">Run</button>
      <button data-refresh="${w.id}" style="background:var(--border);color:var(--text);border:1px solid var(--yellow);padding:2px 6px;cursor:pointer;font-family:var(--font-body);font-size:10px;">Refresh</button>
    </div>
    <div style="margin-left: 12px; margin-bottom: 8px; display: flex; flex-wrap: wrap; align-items: center;">${steps || '<span style="color:var(--muted);">no steps</span>'}</div>`;
  };

  const render = async () => {
    try {
      const data: any = await api.workflows();
      const wfs: any[] = data?.workflows || [];
      contentEl.innerHTML = wfs.map(renderWorkflow).join("") || '<div style="color: var(--muted);">no workflows</div>';

      contentEl.querySelectorAll("button[data-run]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = (btn as HTMLElement).dataset.run || "";
          try {
            await api.runWorkflow(id);
            render();
          } catch (e) {
            alert((e as Error).message);
          }
        });
      });
      contentEl.querySelectorAll("button[data-refresh]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = (btn as HTMLElement).dataset.refresh || "";
          const fresh: any = await api.getWorkflow(id);
          if (fresh) {
            const idx = wfs.findIndex((w) => w.id === id);
            if (idx >= 0) wfs[idx] = fresh;
            contentEl.innerHTML = wfs.map(renderWorkflow).join("");
          }
        });
      });
    } catch (e) {
      contentEl.innerHTML = `<span style="color: var(--orange-red);">workflows unavailable</span>`;
    }
  };

  formEl.querySelector("#wf-create")?.addEventListener("click", async () => {
    const name = (formEl.querySelector("#wf-name") as HTMLInputElement)?.value || "";
    const stepsStr = (formEl.querySelector("#wf-steps") as HTMLInputElement)?.value || "";
    const steps = stepsStr.split(",").map((s) => ({ description: s.trim(), action: "capability:device.status" })).filter((s) => s.description);
    if (!name || !steps.length) return;
    try {
      await api.createWorkflow({ name, steps });
      (formEl.querySelector("#wf-name") as HTMLInputElement).value = "";
      (formEl.querySelector("#wf-steps") as HTMLInputElement).value = "";
      render();
    } catch (e) {
      alert((e as Error).message);
    }
  });

  render();
  const intervalId = window.setInterval(render, 3000);
  el.addEventListener("disconnect", () => { clearInterval(intervalId); });
}
