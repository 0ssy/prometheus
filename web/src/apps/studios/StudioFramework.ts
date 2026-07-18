import { STUDIOS, STUDIO_CATEGORIES, StudioDefinition, StudioCategory, getStudioById, getStudiosByCategory, getAllCategories } from "./registry";
import { StudioShell, StudioShellOptions, StudioState, CrossStudioContract, CROSS_STUDIO_CONTRACT_VERSION } from "./StudioShell";

export interface StudioFrameworkOptions {
  activeStudioId?: string;
  autoRender?: boolean;
}

export interface StudioController {
  shell: StudioShell;
  mount(container: HTMLElement): void;
  destroy(): void;
  sendMessage(targetStudioId: string, action: string, payload: Record<string, unknown>): Promise<unknown>;
  onMessage(handler: (contract: CrossStudioContract) => Promise<unknown>): void;
}

type StudioFactory = (container: HTMLElement, shell: StudioShell) => void;

class StudioRegistryEntry {
  constructor(
    public readonly definition: StudioDefinition,
    public readonly factory: StudioFactory,
  ) {}
}

export class StudioFramework {
  private static instance: StudioFramework | null = null;
  private activeController: StudioController | null = null;
  private registry: Map<string, StudioRegistryEntry> = new Map();
  private messageHandlers: Map<string, (contract: CrossStudioContract) => Promise<unknown>> = new Map();
  private container: HTMLElement | null = null;

  static getInstance(): StudioFramework {
    if (!StudioFramework.instance) {
      StudioFramework.instance = new StudioFramework();
    }
    return StudioFramework.instance;
  }

  registerStudio(definition: StudioDefinition, factory: StudioFactory): void {
    if (this.registry.has(definition.id)) {
      console.warn(`studio ${definition.id} already registered, overwriting`);
    }
    this.registry.set(definition.id, new StudioRegistryEntry(definition, factory));
  }

  getRegisteredStudios(): StudioDefinition[] {
    return Array.from(this.registry.values()).map((e) => e.definition);
  }

  getRegisteredStudio(id: string): StudioDefinition | undefined {
    return this.registry.get(id)?.definition;
  }

  launchStudio(container: HTMLElement, studioId: string): StudioController | null {
    this.container = container;
    const entry = this.registry.get(studioId);
    if (!entry) {
      console.error(`studio ${studioId} not registered`);
      return null;
    }

    if (this.activeController) {
      this.activeController.destroy();
      this.activeController = null;
    }

    const shell = new StudioShell(container, {
      studioId: entry.definition.id,
      title: entry.definition.name,
      icon: entry.definition.icon,
    });

    const controller: StudioController = {
      shell,
      mount: (c: HTMLElement) => {
        entry.factory(c, shell);
      },
      destroy: () => shell.destroy(),
      sendMessage: (target: string, action: string, payload: Record<string, unknown>) =>
        shell.sendMessage(target, action, payload),
      onMessage: (handler: (contract: CrossStudioContract) => Promise<unknown>) =>
        shell.onMessage(handler),
    };

    this.activeController = controller;
    controller.mount(container);
    return controller;
  }

  closeActiveStudio(): void {
    if (this.activeController) {
      this.activeController.destroy();
      this.activeController = null;
      if (this.container) {
        this.container.innerHTML = "";
      }
    }
  }

  getActiveStudio(): StudioController | null {
    return this.activeController;
  }

  broadcast(action: string, payload: Record<string, unknown>): void {
    for (const [studioId, handler] of this.messageHandlers) {
      try {
        handler({ studioId, action, payload });
      } catch {
        /* swallow broadcast errors */
      }
    }
  }

  static reset(): void {
    StudioFramework.instance = null;
  }
}

export function createStudioBase(container: HTMLElement, options: { studioId: string; title: string; icon: string; description: string }) {
  const { studioId, title, icon, description } = options;

  container.innerHTML = `<div style="display: flex; flex-direction: column; height: 100%; box-sizing: border-box; font-family: var(--font-body);">
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid var(--border); background: var(--bg);">
      <span style="font-size: 18px;">${icon}</span>
      <div>
        <div style="font-family: var(--font-heading); font-size: 12px; color: var(--yellow); text-transform: uppercase;">${title}</div>
        <div style="font-size: 11px; color: var(--muted);">${description}</div>
      </div>
    </div>
    <div id="studio-content-${studioId}" style="flex: 1; overflow-y: auto; padding: 12px; background: var(--bg);"></div>
    <div id="studio-statusbar-${studioId}" style="height: 24px; background: var(--border); display: flex; align-items: center; padding: 0 12px; font-size: 11px; color: var(--muted); gap: 16px;">
      <span>Studio: ${studioId}</span>
      <span id="studio-dirty-${studioId}">Clean</span>
      <span id="studio-time-${studioId}">${new Date().toLocaleTimeString()}</span>
    </div>
  </div>`;

  const content = () => container.querySelector(`#studio-content-${studioId}`) as HTMLElement | null;
  const statusBar = () => container.querySelector(`#studio-statusbar-${studioId}`) as HTMLElement | null;

  return {
    content,
    statusBar,
    setStatus(text: string) {
      const el = statusBar();
      if (el && el.firstChild) {
        el.firstChild.textContent = `Studio: ${studioId} — ${text}`;
      }
    },
    setDirty(dirty: boolean) {
      const dirtyEl = container.querySelector(`#studio-dirty-${studioId}`) as HTMLElement | null;
      if (dirtyEl) {
        dirtyEl.textContent = dirty ? "Unsaved changes" : "Clean";
        dirtyEl.style.color = dirty ? "var(--orange-red)" : "var(--muted)";
      }
    },
  };
}

export { STUDIOS, STUDIO_CATEGORIES, StudioCategory, StudioDefinition, getStudioById, getStudiosByCategory, getAllCategories, CROSS_STUDIO_CONTRACT_VERSION };
