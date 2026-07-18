export interface ReloadEvent {
  pluginId: string;
  timestamp: string;
  previousState: Record<string, unknown>;
}

export type ReloadHandler = (event: ReloadEvent) => void;

export class PluginHotReload {
  private watchers: Map<string, { pluginId: string; state: Record<string, unknown>; timer: number | null }> = new Map();
  private handlers: Set<ReloadHandler> = new Set();
  private debounceMs = 300;

  watch(pluginId: string, _directory: string): () => void {
    const entry: { pluginId: string; state: Record<string, unknown>; timer: number | null } = {
      pluginId,
      state: {},
      timer: null,
    };

    entry.timer = window.setInterval(() => {
      this.checkAndReload(pluginId, entry);
    }, 2000);

    this.watchers.set(pluginId, entry);
    return () => this.unwatch(pluginId);
  }

  unwatch(pluginId: string): void {
    const watcher = this.watchers.get(pluginId);
    if (!watcher) return;
    if (watcher.timer !== null) {
      clearInterval(watcher.timer);
    }
    this.watchers.delete(pluginId);
  }

  onReload(handler: ReloadHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  getWatchedPlugins(): string[] {
    return Array.from(this.watchers.keys());
  }

  private async checkAndReload(pluginId: string, entry: { pluginId: string; state: Record<string, unknown>; timer: number | null }): Promise<void> {
    let changed = false;
    const pathsToCheck = [
      `/plugins/installed/${pluginId}/index.ts`,
      `/plugins/installed/${pluginId}/manifest.json`,
    ];

    for (const path of pathsToCheck) {
      try {
        const response = await fetch(path, { method: "HEAD", cache: "no-store" });
        if (response.ok) {
          const lastModified = response.headers.get("last-modified");
          if (lastModified && lastModified !== (entry.state as Record<string, string>)[path]) {
            (entry.state as Record<string, string>)[path] = lastModified;
            changed = true;
          }
        }
      } catch {
        /* ignore check errors */
      }
    }

    if (!changed) return;

    const existing = entry.timer;
    if (existing !== null) clearTimeout(existing);

    entry.timer = window.setTimeout(() => {
      entry.timer = null;
      this.emitReload(pluginId, entry.state);
    }, this.debounceMs) as unknown as number;
  }

  private async emitReload(pluginId: string, previousState: Record<string, unknown>): Promise<void> {
    const event: ReloadEvent = {
      pluginId,
      timestamp: new Date().toISOString(),
      previousState: { ...previousState },
    };

    for (const handler of this.handlers) {
      try {
        await handler(event);
      } catch {
        /* swallow handler errors */
      }
    }

    try {
      const response = await fetch(`/api/plugins/${encodeURIComponent(pluginId)}/reload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!response.ok) {
        console.error(`hot-reload failed for ${pluginId}: ${response.status}`);
      }
    } catch (e) {
      console.error(`hot-reload error for ${pluginId}:`, e);
    }
  }
}

export const pluginHotReload = new PluginHotReload();
