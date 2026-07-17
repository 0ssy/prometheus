export function loadingState(): HTMLElement {
  const el = document.createElement("div");
  el.className = "state-loading";
  el.innerHTML = `<div class="spinner"></div><div style="color:var(--muted); font-size:11px; margin-top:4px;">Loading...</div>`;
  return el;
}

export function errorState(message: string, onRetry?: () => void): HTMLElement {
  const el = document.createElement("div");
  el.className = "state-error";
  el.innerHTML = `<div style="color:var(--orange-red); font-size:11px; margin-bottom:4px;">${message}</div>${onRetry ? '<button class="retry-btn">Retry</button>' : ""}`;
  if (onRetry) {
    el.querySelector(".retry-btn")?.addEventListener("click", onRetry);
  }
  return el;
}

export function emptyState(message: string): HTMLElement {
  const el = document.createElement("div");
  el.className = "state-empty";
  el.innerHTML = `<div style="color:var(--muted); font-size:11px; font-style:italic;">${message}</div>`;
  return el;
}

export function withLifecycle(root: HTMLElement, load: () => Promise<void>) {
  root.innerHTML = "";
  const container = document.createElement("div");
  container.style.cssText = "width:100%; height:100%; display:flex; flex-direction:column;";
  root.appendChild(container);

  const content = document.createElement("div");
  content.style.cssText = "flex:1; min-height:0; overflow-y:auto;";
  container.appendChild(content);

  async function run() {
    content.innerHTML = "";
    content.appendChild(loadingState());
    try {
      await load();
    } catch (e) {
      content.innerHTML = "";
      content.appendChild(errorState(`Failed to load: ${(e as Error)?.message ?? e}`));
    }
  }

  run();
  return { run, content };
}
