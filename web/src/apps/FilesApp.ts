import { sdk } from "../sdk";

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
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
      <div style="font-family: var(--font-heading); color: var(--yellow); font-size: 12px; letter-spacing: 1px;">FILES</div>
      <div style="display:flex; gap:6px;">
        <button id="files-upload" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:2px 6px; cursor:pointer; font-size:11px;">Upload</button>
        <button id="files-refresh" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:2px 6px; cursor:pointer; font-size:11px;">Refresh</button>
      </div>
    </div>
    <div id="files-bc" style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px; font-size:11px;"></div>
    <input id="files-search" type="text" placeholder="search files..." style="margin-bottom:6px; background:var(--bg); color:var(--text); border:1px solid var(--border); padding:2px 4px; font-family:var(--font-mono); font-size:11px;" />
    <div style="display:flex; flex:1; min-height:0; gap:8px;">
      <div id="files-sidebar" style="width:120px; border-right:1px solid var(--border); overflow-y:auto; padding-right:6px;"></div>
      <div id="files-main" style="flex:1; overflow-y:auto; padding-left:6px;"></div>
      <div id="files-preview" style="width:160px; border-left:1px solid var(--border); overflow-y:auto; padding-left:6px; display:none;"></div>
    </div>
  </div>`;

  const bc = el.querySelector("#files-bc") as HTMLElement;
  const sidebar = el.querySelector("#files-sidebar") as HTMLElement;
  const main = el.querySelector("#files-main") as HTMLElement;
  const preview = el.querySelector("#files-preview") as HTMLElement;
  const searchInput = el.querySelector("#files-search") as HTMLInputElement;
  let currentPath = "";
  let selectedFile: string | null = null;

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
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  async function load(path: string, query?: string) {
    currentPath = path;
    renderBreadcrumb(path);
    main.innerHTML = '<div style="color:var(--muted); font-size:11px;">loading...</div>';
    try {
      const f: any = query ? await sdk.files.search(query) : await sdk.files.list(path);
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
      const entries = query ? (f.results ?? f.entries ?? []) : (f.entries ?? []);
      if (!entries || entries.length === 0) {
        const empty = document.createElement("div");
        empty.style.cssText = "color:var(--muted); padding:12px 4px; font-size:11px;";
        empty.textContent = query ? "No matches" : "Folder is empty";
        main.appendChild(empty);
        return;
      }
      for (const entry of entries) {
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
          const fileName = isDir ? `${path ? path + "/" : ""}${entry.name}` : entry.name;
          selectedFile = fileName;
          if (isDir) {
            load(`${path ? path + "/" : ""}${entry.name}`);
            preview.style.display = "none";
          } else if (fileName) {
            showPreview(fileName, entry);
          }
        });
        main.appendChild(row);
      }
    } catch (e) {
      main.innerHTML = `<span style="color:var(--orange-red);">files unavailable (${(e as Error)?.message ?? e})</span>`;
    }
  }

  async function showPreview(name: string, entry: any) {
    preview.style.display = "block";
    preview.innerHTML = `<div style="font-family:var(--font-heading); color:var(--yellow); font-size:11px; margin-bottom:4px;">PREVIEW</div>`;
    const meta = document.createElement("div");
    meta.style.cssText = "font-size:11px; color:var(--muted); margin-bottom:6px;";
    meta.innerHTML = `<div>size: ${formatSize(entry.size)}</div><div>modified: ${formatDate(entry.modified)}</div>`;
    preview.appendChild(meta);
    const actions = document.createElement("div");
    actions.style.cssText = "display:flex; flex-direction:column; gap:4px;";
    actions.innerHTML = `
      <button id="file-dl" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:2px 4px; cursor:pointer; font-size:10px;">Download</button>
      <button id="file-git" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:2px 4px; cursor:pointer; font-size:10px;">Git Status</button>
    `;
    preview.appendChild(actions);
    (preview.querySelector("#file-dl") as HTMLElement).addEventListener("click", () => {
      if (!name) return;
      const a = document.createElement("a");
      a.href = sdk.files.download(name);
      a.download = name.split("/").pop() || name;
      a.click();
    });
    (preview.querySelector("#file-git") as HTMLElement).addEventListener("click", async () => {
      if (!name) return;
      try {
        const status: any = await sdk.files.gitStatus(name);
        meta.innerHTML += `<div style="margin-top:4px; color:var(--steel);">git: ${status?.status ?? "clean"}</div>`;
      } catch {
        meta.innerHTML += `<div style="margin-top:4px; color:var(--orange);">git: unavailable</div>`;
      }
    });
  }

  (el.querySelector("#files-upload") as HTMLElement).addEventListener("click", async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.addEventListener("change", async () => {
      for (const file of Array.from(input.files || [])) {
        try {
          await sdk.files.upload(currentPath, file);
        } catch (e) {
          console.error("upload failed", e);
        }
      }
      load(currentPath);
    });
    input.click();
  });

  (el.querySelector("#files-refresh") as HTMLElement).addEventListener("click", () => {
    load(currentPath);
  });

  searchInput.addEventListener("input", () => {
    const q = searchInput.value.trim();
    if (q) load("", q);
  });

  el.addEventListener("dragover", (e) => {
    e.preventDefault();
    el.style.border = "1px dashed var(--yellow)";
  });
  el.addEventListener("dragleave", () => {
    el.style.border = "";
  });
  el.addEventListener("drop", async (e) => {
    e.preventDefault();
    el.style.border = "";
    const files = Array.from(e.dataTransfer?.files || []);
    for (const file of files) {
      try {
        await sdk.files.upload(currentPath, file);
      } catch (err) {
        console.error("drop upload failed", err);
      }
    }
    load(currentPath);
  });

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
