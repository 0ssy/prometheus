import { api } from "../api/client";

export function mountFiles(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">FILES</div>
    <div id="files-breadcrumb" style="color: var(--muted); margin-bottom: 8px;">/</div>
    <div id="files-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 8px;"></div>
  </div>`;
  const list = el.querySelector("#files-list") as HTMLElement;
  const breadcrumb = el.querySelector("#files-breadcrumb") as HTMLElement;
  let currentPath = "";
  function load(path: string) {
    currentPath = path;
    api.files(path).then((f: any) => {
      breadcrumb.textContent = f.path || "/";
      list.innerHTML = "";
      if (f.entries) {
        for (const entry of f.entries) {
          const card = document.createElement("div");
          card.style.cssText = "border: 1px solid var(--border); padding: 8px; background: var(--bg); cursor: pointer; text-align: center;";
          card.innerHTML = `<div style="font-size: 24px;">${entry.type === "directory" ? "[]" : "{}"}</div><div style="font-size: 14px; color: var(--text);">${entry.name}</div>`;
          card.addEventListener("click", () => {
            if (entry.type === "directory") load(`${path}${path ? "/" : ""}${entry.name}`);
          });
          list.appendChild(card);
        }
      }
    });
  }
  load("");
}
