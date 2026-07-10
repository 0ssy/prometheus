import { api } from "../api/client";

export function mountJobs(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">JOBS</div>
    <div id="jobs-filters" style="margin-bottom: 8px; display: flex; gap: 6px; flex-wrap: wrap;"></div>
    <div id="jobs-content"></div>
  </div>`;
  const filtersEl = el.querySelector("#jobs-filters") as HTMLElement;
  const contentEl = el.querySelector("#jobs-content") as HTMLElement;

  const stateColors: Record<string, string> = {
    scheduled: "var(--muted)",
    running: "var(--yellow)",
    paused: "var(--steel)",
    completed: "#7CFC7C",
    failed: "var(--orange-red)",
  };

  const render = async () => {
    try {
      const data: any = await api.systemJobs();
      const jobs: any[] = data?.jobs || [];
      const states = Array.from(new Set(jobs.map((j) => j.status)));
      filtersEl.innerHTML = states.map((s) => `<span class="tag" style="cursor:pointer;color:${stateColors[s] || "var(--text)"}">${s}</span>`).join("");

      const rows = jobs.map((j: any) => {
        const color = stateColors[j.status] || "var(--text)";
        const next = j.next_run ? new Date(j.next_run * 1000).toLocaleTimeString("en-GB") : "--:--:--";
        return `<div class="node-row" style="flex-wrap:wrap;gap:4px;">
          <span style="flex:1;">${j.name}</span>
          <span class="tag" style="color:${color}">${j.status}</span>
          <span style="color:var(--muted);font-size:10px;">next: ${next}</span>
          <span style="color:var(--muted);font-size:10px;">fails: ${j.failures}</span>
          <button data-action="pause" data-name="${j.name}" style="background:var(--border);color:var(--text);border:1px solid var(--yellow);padding:2px 6px;cursor:pointer;font-family:var(--font-body);font-size:10px;">Pause</button>
          <button data-action="resume" data-name="${j.name}" style="background:var(--border);color:var(--text);border:1px solid var(--yellow);padding:2px 6px;cursor:pointer;font-family:var(--font-body);font-size:10px;">Resume</button>
          <button data-action="trigger" data-name="${j.name}" style="background:var(--border);color:var(--text);border:1px solid var(--yellow);padding:2px 6px;cursor:pointer;font-family:var(--font-body);font-size:10px;">Trigger</button>
        </div>`;
      }).join("");
      contentEl.innerHTML = rows || '<div style="color: var(--muted);">no jobs</div>';

      contentEl.querySelectorAll("button[data-action]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const name = (btn as HTMLElement).dataset.name || "";
          const action = (btn as HTMLElement).dataset.action || "";
          try {
            await api.jobAction(name, action);
            render();
          } catch (e) {
            alert((e as Error).message);
          }
        });
      });
    } catch (e) {
      contentEl.innerHTML = `<span style="color: var(--orange-red);">jobs unavailable</span>`;
    }
  };

  render();
  const intervalId = window.setInterval(render, 2000);
  el.addEventListener("disconnect", () => { clearInterval(intervalId); });
}
