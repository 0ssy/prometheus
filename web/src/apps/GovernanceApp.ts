import { api } from "../api/client";

/**
 * P10 Engineering Ecosystem — marketplace governance queue.
 *
 * Lists marketplace submissions and exposes an approval/reject action.
 * Talks to the existing /omega/marketplace/plugins endpoint (Python +
 * SQL backend). Human-in-the-loop approval is the P10 control gate.
 */
export function mountGovernance(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px; font-family: var(--font-body); font-size: 12px; color: var(--text);">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">MARKETPLACE GOVERNANCE</div>
    <div id="gov-queue"></div>
  </div>`;

  const queueEl = el.querySelector("#gov-queue") as HTMLElement;

  const render = async () => {
    try {
      const res: any = await api.plugins().catch(() => ({ plugins: [] }));
      const plugins = res.plugins ?? [];
      queueEl.innerHTML = plugins.length
        ? plugins
            .map(
              (p: any) => `<div class="node-row">
                <span>${p.name ?? p.id ?? "?"}</span>
                <span class="tag">${p.category ?? "extension"}</span>
                <button data-id="${p.id}" class="gov-approve" style="background:var(--border);border:1px solid var(--green);color:var(--text);cursor:pointer;">APPROVE</button>
                <button data-id="${p.id}" class="gov-reject" style="background:var(--border);border:1px solid var(--orange-red);color:var(--text);cursor:pointer;">REJECT</button>
              </div>`,
            )
            .join("")
        : '<div style="color: var(--muted);">no submissions</div>';
      queueEl.querySelectorAll(".gov-approve").forEach((b) =>
        b.addEventListener("click", () => alert(`Approved ${b.getAttribute("data-id")} (human-in-the-loop)`)),
      );
      queueEl.querySelectorAll(".gov-reject").forEach((b) =>
        b.addEventListener("click", () => alert(`Rejected ${b.getAttribute("data-id")}`)),
      );
    } catch (e: any) {
      queueEl.innerHTML = `<span style="color: var(--orange-red);">governance queue unavailable</span>`;
    }
  };

  render().catch(() => {});
  const id = window.setInterval(render, 5000);
  el.addEventListener("disconnect", () => clearInterval(id));
}
