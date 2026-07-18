import { createStudioBase } from "./StudioFramework";

export interface AILabOptions {
  container: HTMLElement;
  shell: import("./StudioShell").StudioShell;
}

export function mountAILab({ container, shell }: AILabOptions): void {
  const base = (container.querySelector("#studio-main") as HTMLElement) || container;
  const ui = createStudioBase(base, {
    studioId: "ai",
    title: "AI Lab",
    icon: "🧠",
    description: "Model management, inference, RAG indexing, and fine-tuning.",
  });

  const content = ui.content();
  if (!content) return;

  content.innerHTML = `
    <div style="margin-bottom: 12px; font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">AI / ML</div>
    <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center;">
      <select id="ai-model" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="gpt-4">GPT-4</option>
        <option value="claude-3">Claude 3</option>
        <option value="llama-3">Llama 3</option>
        <option value="prometheus-local">Prometheus Local</option>
      </select>
      <select id="ai-action" style="background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-size: 14px;">
        <option value="inference">Run Inference</option>
        <option value="rag">RAG Index</option>
        <option value="finetune">Fine-Tune</option>
        <option value="evaluate">Evaluate</option>
      </select>
      <button id="ai-run" style="background: var(--border); color: var(--text); border: 1px solid var(--cyan); padding: 4px 10px; cursor: pointer;">Run</button>
    </div>
    <div id="ai-log" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 13px; font-family: var(--font-mono); min-height: 200px;"></div>
  `;

  const log = content.querySelector("#ai-log") as HTMLElement;
  const modelSelect = content.querySelector("#ai-model") as HTMLSelectElement;
  const actionSelect = content.querySelector("#ai-action") as HTMLSelectElement;
  const runBtn = content.querySelector("#ai-run") as HTMLElement;

  function line(text: string, color = "var(--text)") {
    const span = document.createElement("div");
    span.style.color = color;
    span.textContent = text;
    log.appendChild(span);
    log.scrollTop = log.scrollHeight;
  }

  runBtn.addEventListener("click", async () => {
    const model = modelSelect.value;
    const action = actionSelect.value;
    line(`> ${action} with ${model}...`, "var(--muted)");
    ui.setStatus("running");
    try {
      await new Promise((r) => setTimeout(r, 1000));
      line(`${action} complete. tokens: 142, latency: 320ms`, "var(--green)");
      ui.setStatus("ready");
      ui.setDirty(false);
    } catch (e: any) {
      line(`error: ${e.message}`, "var(--orange-red)");
      ui.setStatus("error");
    }
  });

  line("AI Lab ready. Select a model and action.", "var(--muted)");
  ui.setStatus("ready");
}
