import { sdk } from "../sdk";

export function mountAssistant(el: HTMLElement) {
  el.innerHTML = `<div style="padding: 4px; display: flex; flex-direction: column; height: 100%; box-sizing: border-box;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 8px;">
      <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow);">ASSISTANT</div>
      <select id="assistant-provider" style="background:var(--bg); color:var(--text); border:1px solid var(--border); padding:1px 4px; font-family:var(--font-mono); font-size:11px;">
        <option value="">default</option>
      </select>
    </div>
    <div id="assistant-output" style="flex: 1; overflow-y: auto; background: var(--bg); border: 1px solid var(--border); padding: 8px; white-space: pre-wrap; font-size: 15px;"></div>
    <div id="assistant-tools" style="display:none; border: 1px solid var(--border); padding: 6px; margin-top: 6px; background: var(--bg);"></div>
    <div style="display: flex; gap: 8px; margin-top: 8px;">
      <input id="assistant-input" style="flex: 1; background: var(--bg); color: var(--text); border: 1px solid var(--border); padding: 6px; font-family: var(--font-body); font-size: 16px;" placeholder="Ask something..." />
      <button id="assistant-send" style="background: var(--border); color: var(--text); border: 1px solid var(--yellow); padding: 4px 8px; cursor: pointer;">SEND</button>
    </div>
  </div>`;
  const input = el.querySelector("#assistant-input") as HTMLInputElement;
  const output = el.querySelector("#assistant-output") as HTMLElement;
  const send = el.querySelector("#assistant-send") as HTMLButtonElement;
  const providerSelect = el.querySelector("#assistant-provider") as HTMLSelectElement;
  const toolsDiv = el.querySelector("#assistant-tools") as HTMLElement;

  async function loadProviders() {
    try {
      const providers: any = await sdk.assistant.providers();
      const items = Array.isArray(providers) ? providers : providers?.providers ?? [];
      for (const p of items) {
        const opt = document.createElement("option");
        opt.value = p.id || p.name || "";
        opt.textContent = p.name || p.id || "unknown";
        providerSelect.appendChild(opt);
      }
    } catch {
      // providers unavailable
    }
  }

  loadProviders();

  async function run() {
    const text = input.value.trim();
    if (!text) return;
    output.innerHTML += "\n> " + text + "\n";
    input.value = "";
    toolsDiv.style.display = "none";
    toolsDiv.innerHTML = "";
    const provider = providerSelect.value || undefined;
    try {
      const stream = await sdk.assistant.stream(text, provider);
      if (!stream) {
        output.innerHTML += "\n[streaming unavailable]\n";
        return;
      }
      const reader = stream.getReader();
      let chunk = document.createElement("div");
      chunk.style.cssText = "color: var(--text); margin-bottom: 4px;";
      output.appendChild(chunk);
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (value) {
          chunk.textContent += decoder.decode(value);
          output.scrollTop = output.scrollHeight;
        }
      }
    } catch (e: any) {
      output.innerHTML += "\nError: " + (e?.message ?? e) + "\n";
      try {
        const res: any = await sdk.assistant.ask(text, provider);
        output.innerHTML += (res.response ?? "") + "\n";
        if (res.tool_calls) renderToolCalls(res.tool_calls);
      } catch (e2: any) {
        output.innerHTML += "Error: " + (e2?.message ?? e2) + "\n";
      }
    }
    output.scrollTop = output.scrollHeight;
  }

  function renderToolCalls(toolCalls: any[]) {
    toolsDiv.style.display = "block";
    toolsDiv.innerHTML = "";
    const title = document.createElement("div");
    title.style.cssText = "font-family:var(--font-heading); font-size:11px; color:var(--yellow); margin-bottom:4px;";
    title.textContent = "TOOL CALLS";
    toolsDiv.appendChild(title);
    for (const tc of toolCalls) {
      const row = document.createElement("div");
      row.className = "node-row";
      row.style.cssText = "display:flex; gap:6px; align-items:center; margin-bottom:4px;";
      const name = document.createElement("span");
      name.textContent = tc.name ?? tc.tool ?? "tool";
      name.style.cssText = "color:var(--text); font-size:12px;";
      const args = document.createElement("span");
      args.style.cssText = "color:var(--muted); font-size:11px; font-family:var(--font-mono);";
      args.textContent = JSON.stringify(tc.arguments ?? tc.args ?? {});
      const approve = document.createElement("button");
      approve.textContent = "Approve";
      approve.style.cssText = "background:var(--border); color:var(--text); border:1px solid var(--yellow); padding:1px 6px; cursor:pointer; font-size:10px;";
      approve.addEventListener("click", async () => {
        try {
          const res = await sdk.assistant.toolCall(tc.name ?? tc.tool ?? "", tc.arguments ?? tc.args ?? {}, true);
          row.innerHTML += `<span style="color:var(--green); font-size:11px;">done</span>`;
          console.log("tool result", res);
        } catch (e) {
          row.innerHTML += `<span style="color:var(--orange-red); font-size:11px;">failed</span>`;
        }
      });
      row.appendChild(name);
      row.appendChild(args);
      row.appendChild(approve);
      toolsDiv.appendChild(row);
    }
  }

  send.addEventListener("click", run);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") run();
  });
}
