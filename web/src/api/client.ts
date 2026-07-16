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
  async delete<T>(path: string): Promise<T> {
    const res = await fetch(API_BASE + path, { method: "DELETE" });
    if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
    return res.json();
  },
};

export const api = {
  status: () => client.get<any>("/status"),
  health: () => client.get<any>("/health"),
  version: () => client.get<any>("/version"),
  coreStatus: () => client.get<any>("/core/status"),
  agents: () => client.get<{ agents: any[] }>("/agents"),
  knowledgeGraph: () => client.get<{ nodes: any[]; edges: any[]; truncated?: boolean; truncated_total?: number }>("/knowledge/graph"),
  knowledgeTimeline: () => client.get<any>("/knowledge/timeline"),
  simulationList: () => client.get<{ runs: any[] }>("/simulation/list"),
  simulationRun: (deviceId: string, failureMode?: string) =>
    client.post("/simulation/run", { device_id: deviceId, failure_mode: failureMode || "disconnect" }),
  files: (path?: string) => client.get<any>(`/files${path ? "?path=" + encodeURIComponent(path) : ""}`),
  hardware: () => client.get<any>("/hardware"),
  assistant: (prompt: string) => client.post("/assistant", { prompt }),
  devices: () => client.get<any>("/devices"),
  device: (id: string) => client.get<any>(`/devices/${id}`),
  devicesSimulated: (deviceId: string) =>
    client.post(`/devices/simulated?device_id=${encodeURIComponent(deviceId)}`),
  gammaFirmware: (path: string) => client.get<any>(`/gamma/firmware?path=${encodeURIComponent(path)}`),
  declareOwnership: (targetId: string, note?: string) =>
    client.post(`/ownership/declare?target_id=${encodeURIComponent(targetId)}${note ? "&note=" + encodeURIComponent(note) : ""}`),
  epsilonRecovery: (deviceId: string) => client.post(`/epsilon/recovery/${encodeURIComponent(deviceId)}`),
  memory: () => client.get<any>("/memory"),
  plugins: () => client.get<{ plugins: any[] }>("/omega/marketplace/plugins"),
  facts: () => client.get<any>("/knowledge"),
  observability: () => client.get<any>("/observability"),
  capabilities: () => client.get<any>("/capabilities"),
  executeCapability: (
    name: string,
    payload: Record<string, unknown>,
    grantedPermissions?: string[],
  ) =>
    client.post<{ ok: boolean; data?: any; error?: string }>(
      "/capabilities/execute",
      { name, payload, granted_permissions: grantedPermissions ?? [] },
    ),
  executeEngineering: (
    moduleName: string,
    workflow: string,
    payload?: Record<string, unknown>,
  ) =>
    client.post<{ ok: boolean; data?: any; error?: string }>(
      "/engineering/execute",
      { module_name: moduleName, workflow, payload },
    ),
  engineeringModules: () => client.get<{ modules: string[] }>("/engineering/modules"),
  titanModules: () => client.get<{ modules: string[] }>("/titan/modules"),
  executeTitan: (
    moduleName: string,
    workflow: string,
    payload?: Record<string, unknown>,
  ) =>
    client.post<{ ok: boolean; data?: any; error?: string }>(
      "/titan/execute",
      { module_name: moduleName, workflow, payload },
    ),
  createDataset: (payload: Record<string, unknown>) => client.post("/titan/datasets", payload),
  getDataset: (id: string) => client.get<any>(`/titan/datasets/${id}`),
  submitFinetune: (payload: Record<string, unknown>) => client.post("/titan/finetune", payload),
  getFinetuneJob: (id: string) => client.get<any>(`/titan/finetune/${id}`),
  registerModel: (payload: Record<string, unknown>) => client.post("/titan/models", payload),
  listModels: (tag?: string) =>
    tag ? client.get<any>(`/titan/models?tag=${encodeURIComponent(tag)}`) : client.get<any>("/titan/models"),
  systemResources: () => client.get<any>("/system/resources"),
  systemJobs: () => client.get<any>("/system/jobs"),
  jobAction: (name: string, action: string) => client.post(`/system/jobs/${encodeURIComponent(name)}/${encodeURIComponent(action)}`),
  workflows: () => client.get<any>("/workflows"),
  createWorkflow: (payload: { name: string; steps: any[] }) => client.post("/workflows", payload),
  runWorkflow: (id: string) => client.post(`/workflows/${encodeURIComponent(id)}/run`),
  getWorkflow: (id: string) => client.get<any>(`/workflows/${encodeURIComponent(id)}`),
  baseline: () => client.get<any>("/system/baseline"),
  baselineRefresh: () => client.post("/system/baseline/refresh"),
  systemServices: () => client.get<any>("/system/services"),
  systemNativeRuntime: () => client.get<any>("/system/native-runtime"),
  events: () => client.get<any>("/events"),
  commands: (payload: Record<string, unknown>) => client.post<any>("/commands", payload),
  capabilitiesHistory: () => client.get<any>("/capabilities/history"),
  distributedNodes: () => client.get<any>("/omega/distributed/nodes"),
  marketplacePluginsPost: (payload: Record<string, unknown>) =>
    client.post("/omega/marketplace/plugins", payload),
  ownership: () => client.get<any>("/ownership"),
  ownershipDelete: (id: string) => client.delete<any>(`/ownership/${encodeURIComponent(id)}`),
  deviceDisconnect: (id: string) => client.post(`/devices/${encodeURIComponent(id)}/disconnect`),
  deviceWrite: (id: string, value: unknown) =>
    client.post(`/devices/${encodeURIComponent(id)}/write`, { value }),
  devicesSerial: (payload: Record<string, unknown>) => client.post("/devices/serial", payload),
};
