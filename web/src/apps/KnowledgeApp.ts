import { api } from "../api/client";
import { store } from "../os/Store";

export function mountKnowledge(el: HTMLElement) {
  el.innerHTML = `<div id="knowledge-app" style="padding: 12px; position: relative; width: 100%; height: 100%; box-sizing: border-box;"></div>`;
  const root = el.querySelector("#knowledge-app") as HTMLElement;
  if (!root) return;
  root.style.display = "flex";
  root.style.flexDirection = "column";
  root.style.gap = "8px";

  const header = document.createElement("div");
  header.style.fontFamily = "var(--font-heading)";
  header.style.fontSize = "12px";
  header.style.color = "var(--yellow)";
  header.textContent = "KNOWLEDGE GRAPH";
  root.appendChild(header);

  const stats = document.createElement("div");
  stats.style.display = "flex";
  stats.style.gap = "16px";
  stats.style.fontSize = "16px";
  root.appendChild(stats);

  const canvas = document.createElement("div");
  canvas.style.cssText = "flex: 1; border: 1px solid var(--border); position: relative; overflow: hidden;";
  root.appendChild(canvas);

  function load() {
    api.knowledgeGraph().then((data: any) => {
      stats.innerHTML = `nodes: ${data.nodes.length} | edges: ${data.edges.length}`;
      canvas.innerHTML = "";
      const w = canvas.clientWidth || 400;
      const h = canvas.clientHeight || 300;
      for (const n of data.nodes.slice(0, 40)) {
        const dot = document.createElement("div");
        dot.className = "knowledge-node";
        dot.style.left = `${40 + Math.random() * (w - 80)}px`;
        dot.style.top = `${20 + Math.random() * (h - 40)}px`;
        dot.title = `${n.label} (${n.type})`;
        canvas.appendChild(dot);
      }
      for (const e of data.edges.slice(0, 60)) {
        const line = document.createElement("div");
        line.className = "knowledge-edge";
        line.style.left = `${40 + Math.random() * (w - 80)}px`;
        line.style.top = `${20 + Math.random() * (h - 40)}px`;
        line.style.width = `${40 + Math.random() * 120}px`;
        line.style.transform = `rotate(${Math.random() * 360}deg)`;
        canvas.appendChild(line);
      }
    });
  }
  load();
  store.subscribe(load);
}
