import { api } from "../api/client";

export interface AppState {
  status: Record<string, unknown> | null;
  events: any[];
  connected: boolean;
}

const STORE_KEY = "prometheus_os_state";

export class Store {
  state: AppState = {
    status: null,
    events: [],
    connected: false,
  };

  private listeners: Set<(state: AppState) => void> = new Set();
  private eventSource: EventSource | null = null;

  subscribe(listener: (state: AppState) => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    for (const l of this.listeners) l(this.state);
  }

  async loadStatus() {
    try {
      const status = await api.status();
      this.state.status = status as Record<string, unknown>;
      this.state.connected = true;
      this.notify();
    } catch {
      this.state.connected = false;
      this.notify();
    }
  }

  /// Wire the SSE stream from the Python backend. All live updates
  /// (hardware, knowledge, agents, simulation) flow through `/events`
  /// — no polling. Falls back to a one-shot status load if SSE is
  /// unavailable.
  startSSE() {
    if (this.eventSource) return;
    try {
      this.eventSource = new EventSource("/events");
      this.eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          this.state.events.unshift(data);
          if (this.state.events.length > 200) this.state.events.length = 200;
          this.notify();
        } catch {}
      };
      this.eventSource.onerror = () => {
        // SSE unavailable (e.g. older backend); degrade to a single load.
        this.loadStatus();
      };
    } catch {
      this.loadStatus();
    }
  }

  stop() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  pushEvent(event: any) {
    this.state.events.unshift(event);
    if (this.state.events.length > 200) this.state.events.length = 200;
    this.notify();
  }
}

export const store = new Store();
