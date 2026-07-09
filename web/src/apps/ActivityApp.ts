import { store } from "../os/Store";

export function mountActivity(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px;">
    <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); margin-bottom: 8px;">ACTIVITY FEED</div>
    <div id="activity-feed" style="display: flex; flex-direction: column; gap: 2px; overflow-y: auto; max-height: 90%;"></div>
  </div>`;
  const feed = el.querySelector("#activity-feed") as HTMLElement;
  const render = () => {
    feed.innerHTML = "";
    for (const e of store.state.events.slice(0, 60)) {
      const line = document.createElement("div");
      line.style.cssText = "border-bottom: 1px solid var(--border); padding: 2px 0; font-size: 14px;";
      const t = new Date(e.timestamp).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
      const msg = e.data && e.data.message ? e.data.message : e.type;
      line.innerHTML = `<span style="color: var(--lavender); margin-right: 8px;">${t}</span><span style="color: var(--text);">${msg}</span>`;
      feed.appendChild(line);
    }
  };
  render();
  store.subscribe(render);
}
