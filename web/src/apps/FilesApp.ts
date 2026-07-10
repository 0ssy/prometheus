import { api } from "../api/client";

export function mountFiles(el: HTMLElement) {
  const workspaceFolders = [
    "Projects",
    "Research",
    "Models",
    "Agents",
    "Datasets",
    "Plugins",
    "Firmware",
    "Simulations",
    "Exports",
    "Recovery",
  ];
  el.innerHTML = `<div style="display:flex; flex-direction:column; height:300px; font-family: var(--font-body); color: var(--text); background: var(--bg);">
    <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; margin-bottom: 6px; letter-spacing: 1px;">FILES</div>
    <div id="files-bc" style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px; font-size:11px;"></div>
    <div style="display:flex; flex:1; min-height:0; gap:8px;">
      <div id="files-sidebar" style="width:120px; border-right:1px solid var(--border); overflow-y:auto; padding-right:6px;"></div>
      <div id="files-main" style="flex:1; overflow-y:auto; padding-left:6px;"></div>
    </div>
  </div>`;

  const bc = el.querySelector("#files-bc") as HTMLElement;
  const sidebar = el.querySelector("#files-sidebar") as HTMLElement;
  const main = el.querySelector("#files-main") as HTMLElement;
  let currentPath = "";

  function renderBreadcrumb(path: string) {
    if (!path) {
      bc.innerHTML = `<span style="color:var(--yellow);cursor:default;">/</span>`;
      return;
    }
    const parts = path.split("/");
    let html = `<span style="color:var(--yellow);cursor:pointer;" data-bc="">/</span>`;
    let accum = "";
    for (let i = 0; i < parts.length; i++) {
      accum = accum ? accum + "/" + parts[i] : parts[i];
      html += `<span style="color:var(--muted);"> / </span><span style="color:var(--yellow);cursor:pointer;" data-bc="${accum}">${parts[i]}</span>`;
    }
    bc.innerHTML = html;
    bc.querySelectorAll("[data-bc]").forEach((node) => {
      node.addEventListener("click", () => load((node as HTMLElement).getAttribute("data-bc") || ""));
    });
  }

  function formatSize(bytes: number | null | undefined) {
    if (bytes == null) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return Math.round(bytes / (1024 * 1024)) + " MB";
  }

  function formatDate(iso: string | undefined) {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = (n: number) => (n < 10 ? "0" + n : n);
    return (
      d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes())
    );
  }

  function load(path: string) {
    currentPath = path;
    renderBreadcrumb(path);
    main.innerHTML = "";
    api.files(path).then((f: any) => {
      if (currentPath !== (f.path || "")) return;
      if (path) {
        const up = document.createElement("div");
        up.className = "node-row";
        up.style.cssText = "display:flex; gap:8px; padding:3px 4px; cursor:pointer; color:var(--orange);";
        up.innerHTML = `<span>[ .. ]</span><span style="flex:1;">Parent Folder</span>`;
        up.addEventListener("click", () => {
          const parts = currentPath.split("/");
          parts.pop();
          load(parts.join("/"));
        });
        main.appendChild(up);
      }
      if (!f.entries || f.entries.length === 0) {
        const empty = document.createElement("div");
        empty.style.cssText = "color:var(--muted); padding:12px 4px; font-size:11px;";
        empty.textContent = "Folder is empty";
        main.appendChild(empty);
        return;
      }
      for (const entry of f.entries) {
        const row = document.createElement("div");
        row.className = "node-row";
        const isDir = entry.type === "directory";
        row.style.cssText = `display:flex; gap:8px; padding:3px 4px; cursor:pointer; color:${isDir ? "var(--text)" : "var(--muted)"};`;
        const icon = document.createElement("span");
        icon.textContent = isDir ? "[DIR]" : "[FILE]";
        const name = document.createElement("span");
        name.style.cssText = "flex:1;";
        name.textContent = entry.name;
        const size = document.createElement("span");
        size.style.cssText = "color:var(--steel); font-size:10px; min-width:60px; text-align:right; font-family:var(--font-mono);";
        size.textContent = isDir ? "" : formatSize(entry.size);
        const mod = document.createElement("span");
        mod.style.cssText = "color:var(--steel); font-size:10px; min-width:90px; text-align:right; font-family:var(--font-mono);";
        mod.textContent = isDir ? "" : formatDate(entry.modified);
        row.appendChild(icon);
        row.appendChild(name);
        row.appendChild(size);
        row.appendChild(mod);
        row.addEventListener("click", () => {
          if (isDir) load(`${path ? path + "/" : ""}${entry.name}`);
        });
        main.appendChild(row);
      }
    });
  }

  for (const folder of workspaceFolders) {
    const row = document.createElement("div");
    row.className = "node-row";
    row.style.cssText = "display:flex; gap:6px; padding:3px 4px; cursor:pointer; color:var(--text); font-size:12px;";
    const icon = document.createElement("span");
    icon.style.cssText = "color:var(--orange-red); font-family:var(--font-mono);";
    icon.textContent = "[DIR]";
    const label = document.createElement("span");
    label.textContent = folder;
    row.appendChild(icon);
    row.appendChild(label);
    row.addEventListener("click", () => load(folder));
    sidebar.appendChild(row);
  }

  load("");
}
