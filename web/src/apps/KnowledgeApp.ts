import { api } from "../api/client";
import { store } from "../os/Store";

type KGNode = { id: string; label?: string; type?: string; confidence?: number };
type KGEdge = { id: string; source: string; target: string; relation?: string; confidence?: number };
type KGGraph = { nodes?: KGNode[]; edges?: KGEdge[]; truncated?: boolean; truncated_total?: number };
type KGFact = {
  id?: string;
  subject: string;
  predicate: string;
  object: string;
  confidence?: number;
  created_at?: string;
};

function hashId(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

function confColor(c: number): string {
  if (c < 0.4) return "var(--orange-red)";
  if (c < 0.7) return "var(--orange)";
  return "var(--yellow)";
}

function typeColor(type: string | undefined): string {
  switch ((type || "").toLowerCase()) {
    case "concept":
      return "var(--lavender)";
    case "entity":
      return "var(--steel)";
    case "event":
      return "var(--orange)";
    case "fact":
      return "var(--orange-red)";
    default:
      return "var(--yellow)";
  }
}

const GRAPH_LIMIT = 10000;

export function mountKnowledge(el: HTMLElement) {
  el.innerHTML = `<div id="knowledge-app" style="padding:4px; position:relative; width:100%; height:100%; box-sizing:border-box;"></div>`;
  const root = el.querySelector("#knowledge-app") as HTMLElement;
  if (!root) return;
  root.style.display = "flex";
  root.style.flexDirection = "column";
  root.style.gap = "6px";

  const header = document.createElement("div");
  header.style.fontFamily = "var(--font-heading)";
  header.style.fontSize = "12px";
  header.style.color = "var(--yellow)";
  header.textContent = "KNOWLEDGE";
  root.appendChild(header);

  const stats = document.createElement("div");
  stats.style.fontSize = "14px";
  stats.style.color = "var(--muted)";
  root.appendChild(stats);

  const content = document.createElement("div");
  content.style.cssText = "flex:1; display:flex; gap:6px; min-height:0;";
  root.appendChild(content);

  const canvas = document.createElement("div");
  canvas.className = "knowledge-canvas";
  canvas.style.cssText = "flex:1; border:1px solid var(--border); position:relative; overflow:hidden; min-width:0;";
  content.appendChild(canvas);

  const side = document.createElement("div");
  side.style.cssText =
    "width:170px; display:flex; flex-direction:column; gap:6px; overflow-y:auto; border:1px solid var(--border); padding:4px; box-sizing:border-box;";
  content.appendChild(side);

  const searchWrap = document.createElement("div");
  const search = document.createElement("input");
  search.type = "text";
  search.placeholder = "search subject/object...";
  search.style.cssText =
    "width:100%; box-sizing:border-box; background:var(--bg); color:var(--text); border:1px solid var(--border); font-family:var(--font-mono); font-size:14px; padding:2px 4px;";
  searchWrap.appendChild(search);
  side.appendChild(searchWrap);

  const timelineTitle = document.createElement("div");
  timelineTitle.style.cssText = "font-family:var(--font-heading); font-size:10px; color:var(--steel);";
  timelineTitle.textContent = "TIMELINE";
  side.appendChild(timelineTitle);

  const timeline = document.createElement("div");
  timeline.style.cssText = "display:flex; flex-direction:column; gap:4px;";
  side.appendChild(timeline);

  const detailsTitle = document.createElement("div");
  detailsTitle.style.cssText = "font-family:var(--font-heading); font-size:10px; color:var(--steel); margin-top:4px;";
  detailsTitle.textContent = "DETAILS";
  side.appendChild(detailsTitle);

  const details = document.createElement("div");
  details.style.cssText = "display:flex; flex-direction:column; gap:4px; color:var(--text); font-size:14px;";
  side.appendChild(details);

  let nodes: KGNode[] = [];
  let edges: KGEdge[] = [];
  let facts: KGFact[] = [];
  let timelineFacts: KGFact[] = [];
  let selectedId: string | null = null;
  let graphTruncatedTotal: number | null = null;
  const positions = new Map<string, { x: number; y: number }>();

  function computePositions() {
    const w = canvas.clientWidth || 240;
    const h = canvas.clientHeight || 200;
    const maxR = Math.min(w, h) / 2 - 14;
    const golden = 2.399963229728653;
    nodes.forEach((n, i) => {
      const hh = hashId(n.id + ":" + i);
      const angle = hh * 2 * Math.PI * 6 + i * golden;
      const r = Math.sqrt(hashId(n.id)) * maxR + 6;
      const x = w / 2 + r * Math.cos(angle);
      const y = h / 2 + r * Math.sin(angle);
      positions.set(n.id, {
        x: Math.max(8, Math.min(w - 8, x)),
        y: Math.max(8, Math.min(h - 8, y)),
      });
    });
  }

  function renderStats() {
    const f = (store.state.status as any)?.knowledge_facts ?? facts.length;
    let cap = "";
    const total = graphTruncatedTotal ?? Math.max(nodes.length, edges.length);
    if (nodes.length > GRAPH_LIMIT || edges.length > GRAPH_LIMIT) {
      const more = Math.max(0, total - GRAPH_LIMIT);
      cap = ` &nbsp; <span style="color:var(--orange-red)">+${(more || 0).toLocaleString()} more (capped at ${GRAPH_LIMIT.toLocaleString()})</span>`;
    }
    stats.innerHTML = `facts: <span style="color:var(--text)">${f}</span> &nbsp; nodes: <span style="color:var(--text)">${nodes.length}</span> &nbsp; edges: <span style="color:var(--text)">${edges.length}</span>${cap}`;
  }

  function renderGraph() {
    canvas.innerHTML = "";
    for (const e of edges) {
      const s = positions.get(e.source);
      const t = positions.get(e.target);
      if (!s || !t) continue;
      const dx = t.x - s.x;
      const dy = t.y - s.y;
      const dist = Math.hypot(dx, dy);
      const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
      const line = document.createElement("div");
      line.className = "knowledge-edge";
      line.style.left = `${s.x}px`;
      line.style.top = `${s.y}px`;
      line.style.width = `${dist}px`;
      line.style.transform = `rotate(${angle}deg)`;
      line.style.background = confColor(e.confidence ?? 0.5);
      line.style.opacity = "0.7";
      canvas.appendChild(line);
    }
    for (const n of nodes) {
      const p = positions.get(n.id);
      if (!p) continue;
      const dot = document.createElement("div");
      dot.className = "knowledge-node";
      dot.style.left = `${p.x}px`;
      dot.style.top = `${p.y}px`;
      dot.style.background = typeColor(n.type);
      if (n.id === selectedId) {
        dot.style.outline = "2px solid var(--text)";
      }
      dot.title = `${n.label ?? n.id} (${n.type ?? "?"})`;
      dot.addEventListener("click", (ev) => {
        ev.stopPropagation();
        selectedId = n.id;
        renderGraph();
        renderDetails();
      });
      canvas.appendChild(dot);
    }
  }

  function matchQuery(f: KGFact): boolean {
    const q = search.value.trim().toLowerCase();
    if (!q) return true;
    return (
      (f.subject || "").toLowerCase().includes(q) ||
      (f.object || "").toLowerCase().includes(q)
    );
  }

  function confBar(c: number): string {
    const pct = Math.round(Math.max(0, Math.min(1, c)) * 100);
    return `<div class="progress-bar" style="height:6px; margin-top:2px;"><div class="progress-fill" style="width:${pct}%; background:${confColor(c)};"></div></div>`;
  }

  function renderTimeline() {
    timeline.innerHTML = "";
    const sorted = [...timelineFacts].sort((a, b) => {
      const ta = a.created_at ? Date.parse(a.created_at) : 0;
      const tb = b.created_at ? Date.parse(b.created_at) : 0;
      return tb - ta;
    });
    const list = sorted.filter(matchQuery).slice(0, 40);
    if (list.length === 0) {
      timeline.innerHTML = `<div style="color:var(--muted); font-size:13px;">no facts</div>`;
      return;
    }
    for (const f of list) {
      const row = document.createElement("div");
      row.className = "node-row";
      row.style.flexDirection = "column";
      row.style.alignItems = "flex-start";
      row.style.gap = "2px";
      const c = f.confidence ?? 0.5;
      row.innerHTML = `<div><span class="tag">${f.subject}</span> ${f.predicate} <span class="tag">${f.object}</span></div><div style="font-size:12px; color:var(--muted);">conf ${c.toFixed(2)} · ${f.created_at ?? "n/a"}</div>${confBar(c)}`;
      timeline.appendChild(row);
    }
  }

  function renderDetails() {
    details.innerHTML = "";
    if (!selectedId) {
      details.innerHTML = `<div style="color:var(--muted); font-size:13px;">click a node</div>`;
      return;
    }
    const n = nodes.find((x) => x.id === selectedId);
    if (!n) return;
    const head = document.createElement("div");
    head.style.cssText = "font-family:var(--font-heading); font-size:10px; color:var(--yellow);";
    head.textContent = (n.label ?? n.id).toUpperCase();
    details.appendChild(head);

    const meta = document.createElement("div");
    meta.style.cssText = "font-size:13px; color:var(--muted);";
    meta.innerHTML = `type: <span class="tag">${n.type ?? "?"}</span> · conf ${(n.confidence ?? 0).toFixed(2)}`;
    details.appendChild(meta);

    const relTitle = document.createElement("div");
    relTitle.style.cssText = "font-size:12px; color:var(--steel); margin-top:4px;";
    relTitle.textContent = "RELATIONSHIPS";
    details.appendChild(relTitle);

    const outgoing = edges.filter((e) => e.source === n.id);
    if (outgoing.length === 0) {
      const none = document.createElement("div");
      none.style.cssText = "font-size:13px; color:var(--muted);";
      none.textContent = "no outgoing edges";
      details.appendChild(none);
    } else {
      for (const e of outgoing) {
        const t = nodes.find((x) => x.id === e.target);
        const row = document.createElement("div");
        row.className = "node-row";
        const c = e.confidence ?? 0.5;
        row.innerHTML = `<div style="font-size:13px;"><span class="tag">${e.relation ?? "->"}</span> ${(t?.label ?? e.target)}</div><div style="font-size:12px; color:var(--muted);">conf ${c.toFixed(2)}</div>${confBar(c)}`;
        details.appendChild(row);
      }
    }

    const provTitle = document.createElement("div");
    provTitle.style.cssText = "font-size:12px; color:var(--steel); margin-top:4px;";
    provTitle.textContent = "PROVENANCE";
    details.appendChild(provTitle);
    const prov = document.createElement("div");
    prov.style.cssText = "font-size:13px; color:var(--muted);";
    prov.textContent = "source: knowledge graph · 0 facts linked locally";
    details.appendChild(prov);
  }

  function load() {
    Promise.all([
      api.knowledgeGraph().catch(() => ({ nodes: [], edges: [] })),
      api.knowledgeTimeline().catch(() => ({ facts: [] })),
      api.facts().catch(() => []),
    ])
      .then(([graph, tl, fct]) => {
        const g = graph as KGGraph;
        const rawNodes = (g.nodes || []) as KGNode[];
        const rawEdges = (g.edges || []) as KGEdge[];
        graphTruncatedTotal = typeof g.truncated_total === "number" ? g.truncated_total : null;
        const overLimit =
          (g.truncated === true) ||
          rawNodes.length > GRAPH_LIMIT ||
          rawEdges.length > GRAPH_LIMIT;
        nodes = overLimit
          ? rawNodes.slice(0, GRAPH_LIMIT)
          : rawNodes;
        edges = overLimit
          ? rawEdges.slice(0, GRAPH_LIMIT)
          : rawEdges;
        timelineFacts = ((tl && (tl as any).facts) || []) as KGFact[];
        facts = (Array.isArray(fct) ? fct : []) as KGFact[];
        computePositions();
        renderStats();
        renderGraph();
        renderTimeline();
        renderDetails();
      })
      .catch(() => {
        renderStats();
      });
  }

  search.addEventListener("input", renderTimeline);
  canvas.addEventListener("click", () => {
    selectedId = null;
    renderGraph();
    renderDetails();
  });

  load();
  const unsub = store.subscribe(load);
  el.addEventListener("unmount", () => unsub());
}
