import { api } from "../api/client";

export function mountAssistant(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 12px; font-family: var(--font-body); font-size: 16px; display: flex; flex-direction: column; height: 100%;">
    <div style="font-family: var(--font-heading); color: var(--yellow); margin-bottom: 8px;">ASSISTANT</div>
    <div id="assistant-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap;"></div>
    <div style="display: flex; gap: 8px; margin-top: 8px;">
      <input id="assistant-input" style="flex: 1; background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-family: var(--font-body);" placeholder="Ask something..." />
      <button id="assistant-send" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer;">SEND</button>
    </div>
  </div>`;
  const input = el.querySelector("#assistant-input") as HTMLInputElement;
  const output = el.querySelector("#assistant-output") as HTMLElement;
  const send = el.querySelector("#assistant-send") as HTMLButtonElement;
  async function run() {
    const text = input.value.trim();
    if (!text) return;
    output.innerHTML += "\n> " + text + "\n";
    try {
      const res: any = await api.assistant(text);
      output.innerHTML += res.response + "\n";
    } catch (e: any) {
      output.innerHTML += "Error: " + e.message + "\n";
    }
    input.value = "";
    output.scrollTop = output.scrollHeight;
  }
  send.addEventListener("click", run);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
}
