export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: Record<string, unknown>): Promise<T>;
  delete<T>(path: string): Promise<T>;
}

export interface StatusSnapshot {
  kernel: string;
  knowledge: string;
  simulation: string;
  reasoning: string;
  hardware: string;
  devices: number;
  agents: number;
  agent_statuses: AgentStatus[];
  plugins: number;
  capabilities: number;
  knowledge_facts: number;
}

export interface AgentStatus {
  name: string;
  status: string;
  last_task: Record<string, unknown> | null;
  updated_at: string | null;
}

export interface KnowledgeNode {
  id: number;
  label: string;
  type: string;
  confidence: string | null;
}

export interface KnowledgeEdge {
  id: number;
  source: number;
  target: number;
  relation: string;
  confidence: number;
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

export interface SimulationRun {
  id: string;
  device_id: string;
  failure_mode: string;
  status: string;
  progress: string;
  risk: string | null;
  confidence: string | null;
  recovered: string | null;
  impact: string | null;
  result: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface FileEntry {
  type: "file" | "directory";
  name?: string;
  path: string;
  size?: number;
  modified?: string;
  entries?: FileEntry[];
}

export interface HardwareSnapshot {
  hal: Record<string, unknown>;
  devices: Record<string, unknown>[];
  timestamp: string;
}

export interface MessageEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}
