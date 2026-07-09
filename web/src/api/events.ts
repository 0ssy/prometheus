export type EventHandler = (event: MessageEvent) => void;

export function createEventSource(path: string, onEvent: EventHandler, onError?: (err: Event) => void): EventSource {
  const es = new EventSource(path);
  es.onmessage = onEvent;
  if (onError) es.onerror = onError;
  return es;
}
