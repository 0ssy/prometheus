export interface AppWindow {
  id: string;
  title: string;
  icon: string;
  mount(root: HTMLElement): void;
  unmount?(): void;
  tick?(): void;
}
