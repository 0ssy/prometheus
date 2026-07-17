import { client } from "../api/client";
import { kernel } from "../kernel/KernelClient";

export interface SdkEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export type EventHandler = (event: SdkEvent) => void;

class EventBus {
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private source: EventSource | null = null;

  subscribe(type: string, handler: EventHandler): () => void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set());
    this.handlers.get(type)!.add(handler);
    return () => this.handlers.get(type)?.delete(handler);
  }

  start() {
    if (this.source) return;
    try {
      this.source = new EventSource("/events");
      this.source.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data) as SdkEvent;
          this.handlers.get(event.type)?.forEach((h) => h(event));
        } catch {}
      };
      this.source.onerror = () => {
        this.source?.close();
        this.source = null;
      };
    } catch {
      // SSE unavailable
    }
  }

  stop() {
    this.source?.close();
    this.source = null;
  }
}

const events = new EventBus();

export const sdk = {
  events: {
    subscribe: (type: string, handler: EventHandler) => events.subscribe(type, handler),
    start: () => events.start(),
    stop: () => events.stop(),
  },

  kernel: {
    isNative: kernel.isNative,
    terminalSpawn: (shell: string, cols = 80, rows = 24) => kernel.terminalSpawn(shell, cols, rows),
    terminalWrite: (sessionId: string, data: Uint8Array | string) => kernel.terminalWrite(sessionId, data),
    terminalResize: (sessionId: string, cols: number, rows: number) => kernel.terminalResize(sessionId, cols, rows),
    terminalKill: (sessionId: string) => kernel.terminalKill(sessionId),
    terminalRecordCommand: (sessionId: string, line: string) => kernel.terminalRecordCommand(sessionId, line),
    terminalHistory: (sessionId: string, back: number) => kernel.terminalHistory(sessionId, back),
    terminalFind: (sessionId: string, query: string) =>
      typeof (kernel as any).terminalFind === "function"
        ? (kernel as any).terminalFind(sessionId, query)
        : Promise.resolve(null),
    status: () => kernel.kernelStatus(),
    sessionSave: (session: any) => kernel.sessionSave(session),
    sessionRestore: (id: string) => kernel.sessionRestore(id),
  },

  terminal: {
    spawn: (shell: string, cols = 80, rows = 24) =>
      client.post<{ id: string }>("/terminal/spawn", { shell, cols, rows }),
    write: (sessionId: string, data: string) =>
      client.post(`/terminal/${sessionId}/write`, { data }),
    resize: (sessionId: string, cols: number, rows: number) =>
      client.post(`/terminal/${sessionId}/resize`, { cols, rows }),
    kill: (sessionId: string) =>
      client.post(`/terminal/${sessionId}/kill`),
    history: (sessionId: string) =>
      client.get<{ history: string[] }>(`/terminal/${sessionId}/history`),
    find: (sessionId: string, query: string) =>
      client.get<{ matches: { line: number; text: string }[] }>(`/terminal/${sessionId}/find?q=${encodeURIComponent(query)}`),
  },

  hardware: {
    list: () => client.get<any>("/hardware"),
    probe: () => client.post("/hardware/probe"),
    connect: (id: string, transport: string) =>
      client.post(`/hardware/${encodeURIComponent(id)}/connect`, { transport }),
    disconnect: (id: string) =>
      client.post(`/hardware/${encodeURIComponent(id)}/disconnect`),
    read: (id: string, length?: number) =>
      client.post(`/hardware/${encodeURIComponent(id)}/read`, { length }),
    write: (id: string, value: unknown) =>
      client.post(`/hardware/${encodeURIComponent(id)}/write`, { value }),
    recovery: (id: string) => client.post(`/hardware/${encodeURIComponent(id)}/recovery`),
  },

  knowledge: {
    graph: () => client.get<{ nodes: any[]; edges: any[]; truncated?: boolean; truncated_total?: number }>("/knowledge/graph"),
    timeline: () => client.get<any>("/knowledge/timeline"),
    facts: () => client.get<any>("/knowledge"),
    search: (q: string) => client.get<any>(`/knowledge/search?q=${encodeURIComponent(q)}`),
  },

  simulation: {
    run: (deviceId: string, failureMode?: string) =>
      client.post("/simulation/run", { device_id: deviceId, failure_mode: failureMode || "disconnect" }),
    list: () => client.get<{ runs: any[] }>("/simulation/list"),
    cancel: (id: string) => client.post(`/simulation/${encodeURIComponent(id)}/cancel`),
  },

  agents: {
    list: () => client.get<{ agents: any[] }>("/agents"),
    status: () => client.get<any>("/agents/status"),
    dispatch: (name: string, payload: Record<string, unknown>) =>
      client.post(`/agents/${encodeURIComponent(name)}/dispatch`, payload),
  },

  plugins: {
    list: () => client.get<{ plugins: any[] }>("/omega/marketplace/plugins"),
    install: (id: string) => client.post(`/omega/marketplace/plugins/${encodeURIComponent(id)}/install`),
    run: (id: string, payload?: Record<string, unknown>) =>
      client.post(`/omega/marketplace/plugins/${encodeURIComponent(id)}/run`, payload),
  },

  files: {
    list: (path?: string) => client.get<any>(`/files${path ? "?path=" + encodeURIComponent(path) : ""}`),
    upload: (path: string, file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("path", path);
      return fetch("/files/upload", { method: "POST", body: form }).then((r) => r.json());
    },
    download: (path: string) => `/files/download?path=${encodeURIComponent(path)}`,
    search: (q: string) => client.get<any>(`/files/search?q=${encodeURIComponent(q)}`),
    recent: () => client.get<any>("/files/recent"),
    gitStatus: (path: string) => client.get<any>(`/git/status?path=${encodeURIComponent(path)}`),
  },

  assistant: {
    ask: (prompt: string, provider?: string) =>
      client.post("/assistant", { prompt, provider }),
    stream: (prompt: string, provider?: string) => {
      const form = new FormData();
      form.append("prompt", prompt);
      if (provider) form.append("provider", provider);
      return fetch("/assistant/stream", { method: "POST", body: form }).then((r) => {
        if (!r.ok) throw new Error(`assistant stream failed: ${r.status}`);
        return r.body;
      });
    },
    providers: () => client.get<any>("/assistant/providers"),
    toolCall: (tool: string, args: Record<string, unknown>, approved = false) =>
      client.post("/assistant/tools", { tool, args, approved }),
  },

  memory: {
    list: () => client.get<any>("/memory"),
    add: (text: string) => client.post("/memory", { text }),
  },

  commands: {
    run: (payload: Record<string, unknown>) => client.post<any>("/commands", payload),
  },
};
