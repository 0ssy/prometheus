const ONBOARDED_KEY = "prometheus_onboarded";

interface Step {
  title: string;
  html: string;
}

const STEPS: Step[] = [
  {
    title: "WELCOME TO PROMETHEUS",
    html: `<p>You just launched an <b>Engineering Intelligence Operating System</b>, not a web dashboard.</p>
      <p>Everything you see &mdash; kernel, knowledge, agents, simulation, hardware &mdash; is a live subsystem running on your machine.</p>`,
  },
  {
    title: "THE DESKTOP",
    html: `<p>Each capability is an <b>application</b>. The <span class="ob-hl">Dock</span> at the bottom launches them.</p>
      <p>Windows are <span class="ob-hl">movable, resizable, minimizable and maximizable</span> &mdash; just like a real OS. Your layout is remembered between sessions.</p>`,
  },
  {
    title: "THE TERMINAL",
    html: `<p>The terminal at the bottom is <b>always live</b>. Every GUI action has a CLI equivalent.</p>
      <p>Try: <span class="ob-cmd">open knowledge</span> &middot; <span class="ob-cmd">connect phone</span> &middot; <span class="ob-cmd">run simulation</span> &middot; <span class="ob-cmd">help</span></p>`,
  },
  {
    title: "THE FILESYSTEM",
    html: `<p>Every project lives in the built-in <span class="ob-hl">Files</span> workspace &mdash; Projects, Research, Models, Agents, Firmware, Simulations and more.</p>
      <p>Open <b>Files</b> from the dock to explore your engineering workspace.</p>`,
  },
  {
    title: "LIVE SUBSYSTEMS",
    html: `<p>Open <b>Agents</b>, <b>Knowledge</b>, <b>Simulation</b> or <b>Hardware</b> to watch them update in real time as the system runs.</p>
      <p>The <b>Activity Feed</b> (top-right) records every event.</p>`,
  },
  {
    title: "AI ASSISTANT",
    html: `<p>The <b>Assistant</b> can help with engineering tasks once you connect an LLM provider.</p>
      <p>Open <b>Assistant</b> and add your provider (e.g. LM Studio, OpenAI, Ollama) to get started.</p>`,
  },
  {
    title: "YOU'RE ALL SET",
    html: `<p>Press <span class="ob-key">1&ndash;9</span> to open dock apps, <span class="ob-key">\`</span> to focus the terminal, and <span class="ob-key">Ctrl+/</span> any time for the full shortcut list.</p>
      <p>What would you like to build today?</p>`,
  },
];

export function showOnboarding(root: HTMLElement) {
  try {
    if (localStorage.getItem(ONBOARDED_KEY) === "1") return;
  } catch {
    return;
  }

  const overlay = document.createElement("div");
  overlay.id = "onboarding";
  root.appendChild(overlay);

  let i = 0;
  const render = () => {
    const step = STEPS[i];
    const last = i === STEPS.length - 1;
    overlay.innerHTML = `
      <div class="ob-card">
        <div class="ob-steps">
          ${STEPS.map((_, n) => `<span class="ob-dot${n === i ? " active" : ""}${n < i ? " done" : ""}"></span>`).join("")}
        </div>
        <div class="ob-title">${step.title}</div>
        <div class="ob-body">${step.html}</div>
        <div class="ob-actions">
          <button class="ob-btn ghost" id="ob-skip">SKIP</button>
          <div style="flex:1;"></div>
          <button class="ob-btn ghost" id="ob-back" ${i === 0 ? "disabled" : ""}>BACK</button>
          <button class="ob-btn" id="ob-next">${last ? "GET STARTED" : "NEXT"}</button>
        </div>
      </div>`;

    overlay.querySelector("#ob-skip")?.addEventListener("click", finish);
    overlay.querySelector("#ob-back")?.addEventListener("click", () => {
      if (i > 0) {
        i--;
        render();
      }
    });
    overlay.querySelector("#ob-next")?.addEventListener("click", () => {
      if (last) finish();
      else {
        i++;
        render();
      }
    });
  };

  const finish = () => {
    try {
      localStorage.setItem(ONBOARDED_KEY, "1");
    } catch {}
    overlay.remove();
  };

  render();
}
