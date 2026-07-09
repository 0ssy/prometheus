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
  private pollInterval: number | null = null;

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

  startSSE() {
    if (this.eventSource) return;
    this.eventSource = new EventSource("/events");
    if (this.eventSource.onmessage) {
      this.eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          this.state.events.unshift(data);
          if (this.state.events.length > 200) this.state.events.length = 200;
          this.notify();
        } catch {}
      };
    }
    this.startPolling();
  }

  private startPolling() {
    if (this.pollInterval) return;
    this.pollInterval = window.setInterval(() => this.loadStatus(), 5000);
  }

  stop() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  pushEvent(event: any) {
    this.state.events.unshift(event);
    if (this.state.events.length > 200) this.state.events.length = 200;
    this.notify();
  }
}

export const store = new Store();
