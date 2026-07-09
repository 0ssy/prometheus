import { store } from "../os/Store";

export function mountActivity(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">ACTIVITY FEED</div>
    <div id="activity-feed" style="display: flex; flex-direction: column; gap: 4px; overflow-y: auto; max-height: 90%;"></div>
  </div>`;
  const feed = el.querySelector("#activity-feed") as HTMLElement;
  store.subscribe(() => {
    feed.innerHTML = "";
    for (const e of store.state.events.slice(0, 60)) {
      const line = document.createElement("div");
      line.style.cssText = "border-bottom: 1px solid var(--border); padding: 2px 0; font-size: 14px;";
      line.innerHTML = `<span style="color: var(--muted);">${new Date(e.timestamp).toLocaleTimeString()}</span> <span style="color: var(--yellow);">${e.type}</span> <span style="color: var(--text);">${JSON.stringify(e.data)}</span>`;
      feed.appendChild(line);
    }
  });
}
