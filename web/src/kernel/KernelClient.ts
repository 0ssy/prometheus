// Kernel bridge: talks to the Prometheus Rust kernel via Tauri commands when
// running inside the desktop shell, and degrades to a no-op stub when served
// from a plain browser (dev / `vite`). This keeps the bundle free of the
// `@tauri-apps/api` dependency while still functioning inside Tauri.
//
// The Tauri runtime is detected at call time (not import time), so the same
// frontend code path works in both environments.

export interface WindowState {
  id: string;
  app_id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  minimized: boolean;
  maximized: boolean;
  z_order?: number;
}

export interface Session {
  id: string;
  windows: WindowState[];
  terminals?: string[];
  meta?: Record<string, unknown>;
}

export interface KernelStatus {
  healthy: boolean;
  terminals: number;
  session_db: string;
}

function hasTauri(): boolean {
  return (
    typeof window !== "undefined" &&
    ("__TAURI__" in window || "__TAURI_INTERNALS__" in window)
  );
}

// Tauri v2 global API (lazily accessed to avoid bundling the dependency).
interface TauriGlobal {
  invoke<T = unknown>(cmd: string, args?: Record<string, unknown>): Promise<T>;
  listen<T = unknown>(
    event: string,
    handler: (e: { payload: T }) => void,
  ): Promise<() => void>;
}

function tauri(): TauriGlobal {
  // @ts-expect-error - globals are injected by the Tauri runtime.
  return (window.__TAURI__ ?? window.__TAURI_INTERNALS__) as TauriGlobal;
}

function b64encode(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

async function invoke<T = unknown>(cmd: string, args: Record<string, unknown> = {}): Promise<T> {
  if (!hasTauri()) {
    throw new Error(`kernel command '${cmd}' unavailable in browser mode`);
  }
  return tauri().invoke<T>(cmd, args);
}

export const kernel = {
  isNative: hasTauri,

  /** Listen for a kernel/Tauri event (e.g. `terminal-output`). Browser: no-op. */
  async listen<T = unknown>(
    event: string,
    handler: (payload: T) => void,
  ): Promise<() => void> {
    if (!hasTauri()) return () => {};
    return tauri().listen<T>(event, (e) => handler(e.payload));
  },

  async terminalSpawn(shell: string, cols = 80, rows = 24): Promise<string> {
    return invoke<string>("terminal_spawn", { shell, cols, rows });
  },

  async terminalWrite(sessionId: string, data: Uint8Array | string): Promise<void> {
    const bytes =
      typeof data === "string"
        ? new TextEncoder().encode(data)
        : data;
    await invoke("terminal_write", { session_id: sessionId, data: b64encode(bytes) });
  },

  async terminalResize(sessionId: string, cols: number, rows: number): Promise<void> {
    await invoke("terminal_resize", { session_id: sessionId, cols, rows });
  },

  async terminalKill(sessionId: string): Promise<void> {
    await invoke("terminal_kill", { session_id: sessionId });
  },

  async terminalRecordCommand(sessionId: string, line: string): Promise<void> {
    await invoke("terminal_record_command", { session_id: sessionId, line });
  },

  async terminalHistory(sessionId: string, back: number): Promise<string | null> {
    return invoke<{ value: string | null } | string | null>("terminal_history", {
      session_id: sessionId,
      back,
    }) as Promise<string | null>;
  },

  async kernelStatus(): Promise<KernelStatus> {
    return invoke<KernelStatus>("kernel_status");
  },

  async sessionSave(session: Session): Promise<void> {
    await invoke("session_save", { session });
  },

  async sessionSaveWindow(sessionId: string, window: WindowState): Promise<void> {
    await invoke("session_save_window", { session_id: sessionId, window });
  },

  async sessionRestore(id: string): Promise<Session | null> {
    return invoke<Session | null>("session_restore", { id });
  },
};

export type KernelClient = typeof kernel;
