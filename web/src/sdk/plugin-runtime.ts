export type PluginState = "unloaded" | "loading" | "ready" | "running" | "error" | "shutdown";

export interface PluginManifestParsed {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  capabilities: string[];
  permissions: string[];
  entrypoint: string;
  engines: { id: string; version: string; runtime: string }[];
}

export interface PluginContext {
  deviceId?: string;
  payload?: Record<string, unknown>;
  grantedPermissions: string[];
  simulate: boolean;
}

export interface PluginExecutionResult {
  ok: boolean;
  data?: unknown;
  error?: string;
  durationMs: number;
}

export interface PluginLifecycleEvent {
  pluginId: string;
  state: PluginState;
  timestamp: string;
  message?: string;
}

export type PluginEventHandler = (event: PluginLifecycleEvent) => void;

export class PluginRuntime {
  private manifests: Map<string, PluginManifestParsed> = new Map();
  private instances: Map<string, { context: PluginContext; state: PluginState }> = new Map();
  private handlers: Map<PluginState, Set<PluginEventHandler>> = new Map();
  private defaultTimeoutMs = 30_000;

  async loadManifest(manifest: PluginManifestParsed): Promise<void> {
    this.emit({ pluginId: manifest.id, state: "loading", timestamp: new Date().toISOString() });
    this.manifests.set(manifest.id, manifest);
    this.instances.set(manifest.id, { context: { grantedPermissions: [], simulate: false }, state: "ready" });
    this.emit({ pluginId: manifest.id, state: "ready", timestamp: new Date().toISOString(), message: "manifest loaded" });
  }

  async execute(pluginId: string, context: PluginContext): Promise<PluginExecutionResult> {
    const start = performance.now();
    const instance = this.instances.get(pluginId);
    if (!instance) {
      return { ok: false, error: `plugin ${pluginId} not loaded`, durationMs: performance.now() - start };
    }

    const manifest = this.manifests.get(pluginId);
    if (!manifest) {
      return { ok: false, error: `manifest for ${pluginId} not found`, durationMs: performance.now() - start };
    }

    const missingPermissions = manifest.permissions.filter((p) => !context.grantedPermissions.includes(p));
    if (missingPermissions.length > 0) {
      return { ok: false, error: `missing permissions: ${missingPermissions.join(", ")}`, durationMs: performance.now() - start };
    }

    instance.state = "running";
    this.emit({ pluginId, state: "running", timestamp: new Date().toISOString() });
    instance.context = context;

    try {
      const result = await this.runWithTimeout(pluginId, context, start);
      instance.state = "ready";
      this.emit({ pluginId, state: "ready", timestamp: new Date().toISOString() });
      return { ...result, durationMs: performance.now() - start };
    } catch (e: unknown) {
      instance.state = "error";
      const message = e instanceof Error ? e.message : "unknown error";
      this.emit({ pluginId, state: "error", timestamp: new Date().toISOString(), message });
      return { ok: false, error: message, durationMs: performance.now() - start };
    }
  }

  async shutdown(pluginId: string): Promise<void> {
    const instance = this.instances.get(pluginId);
    if (!instance) return;
    instance.state = "shutdown";
    this.emit({ pluginId, state: "shutdown", timestamp: new Date().toISOString() });
    this.instances.delete(pluginId);
  }

  async health(pluginId: string): Promise<{ healthy: boolean; state: PluginState; uptimeMs: number }> {
    const instance = this.instances.get(pluginId);
    if (!instance) return { healthy: false, state: "unloaded", uptimeMs: 0 };
    return { healthy: instance.state !== "error", state: instance.state, uptimeMs: 0 };
  }

  onStateChange(state: PluginState, handler: PluginEventHandler): () => void {
    if (!this.handlers.has(state)) this.handlers.set(state, new Set());
    this.handlers.get(state)!.add(handler);
    return () => this.handlers.get(state)?.delete(handler);
  }

  getLoadedPlugins(): string[] {
    return Array.from(this.manifests.keys());
  }

  private async runWithTimeout(pluginId: string, context: PluginContext, start: number): Promise<PluginExecutionResult> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.defaultTimeoutMs);

    try {
      const response = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: {
            device_id: context.deviceId,
            payload: context.payload,
            granted_permissions: context.grantedPermissions,
            simulate: context.simulate,
          },
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        return { ok: false, error: `HTTP ${response.status}: ${text}`, durationMs: performance.now() - start };
      }

      const data = await response.json();
      return { ok: data.ok ?? true, data: data.data, error: data.error, durationMs: performance.now() - start };
    } catch (e: unknown) {
      if ((e as Error)?.name === "AbortError") {
        return { ok: false, error: `plugin ${pluginId} timed out after ${this.defaultTimeoutMs}ms`, durationMs: performance.now() - start };
      }
      throw e;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private emit(event: PluginLifecycleEvent): void {
    const handlers = this.handlers.get(event.state);
    if (!handlers) return;
    handlers.forEach((h) => {
      try { h(event); } catch { /* swallow handler errors */ }
    });
  }
}

export const pluginRuntime = new PluginRuntime();
