import { ApiClient } from "../types";

const API_BASE = "";

export const client: ApiClient = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(API_BASE + path);
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json();
  },
  async post<T>(path: string, body?: Record<string, unknown>): Promise<T> {
    const res = await fetch(API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
    return res.json();
  },
};

export const api = {
  status: () => client.get<any>("/status"),
  health: () => client.get<any>("/health"),
  version: () => client.get<any>("/version"),
  coreStatus: () => client.get<any>("/core/status"),
  agents: () => client.get<{ agents: any[] }>("/agents"),
  knowledgeGraph: () => client.get<{ nodes: any[]; edges: any[] }>("/knowledge/graph"),
  knowledgeTimeline: () => client.get<any>("/knowledge/timeline"),
  simulationList: () => client.get<{ runs: any[] }>("/simulation/list"),
  simulationRun: (deviceId: string, failureMode?: string) =>
    client.post("/simulation/run", { device_id: deviceId, failure_mode: failureMode || "disconnect" }),
  files: (path?: string) => client.get<any>(`/files${path ? "?path=" + encodeURIComponent(path) : ""}`),
  hardware: () => client.get<any>("/hardware"),
  assistant: (prompt: string) => client.post("/assistant", { prompt }),
  devices: () => client.get<any>("/devices"),
  device: (id: string) => client.get<any>(`/devices/${id}`),
  memory: () => client.get<any>("/memory"),
  plugins: () => client.get<{ plugins: any[] }>("/omega/marketplace/plugins"),
  facts: () => client.get<any>("/knowledge"),
  observability: () => client.get<any>("/observability"),
  capabilities: () => client.get<any>("/capabilities"),
};
