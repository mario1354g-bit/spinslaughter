import type { EmitterEvent } from './types';

type Handler<T extends EmitterEvent = EmitterEvent> = (event: T) => void | Promise<void>;
type HandlerMap = Partial<{ [K in EmitterEvent['type']]: Handler<Extract<EmitterEvent, { type: K }>> }>;

class WarpathEventEmitter {
  private handlers = new Map<string, Set<Handler>>();

  broadcast<T extends EmitterEvent>(event: T): void {
    const handlers = this.handlers.get(event.type);
    if (!handlers) return;
    for (const handler of handlers) {
      void handler(event);
    }
  }

  async broadcastAsync<T extends EmitterEvent>(event: T): Promise<void> {
    const handlers = this.handlers.get(event.type);
    if (!handlers) return;
    await Promise.all(Array.from(handlers).map((handler) => handler(event)));
  }

  waitFor<T extends EmitterEvent['type']>(type: T): Promise<Extract<EmitterEvent, { type: T }>> {
    return new Promise((resolve) => {
      const handler: Handler = (event) => {
        this.handlers.get(type)?.delete(handler);
        resolve(event as Extract<EmitterEvent, { type: T }>);
      };
      if (!this.handlers.has(type)) this.handlers.set(type, new Set());
      this.handlers.get(type)!.add(handler);
    });
  }

  subscribeOnMount(map: HandlerMap): () => void {
    const entries = Object.entries(map) as [string, Handler][];
    for (const [type, handler] of entries) {
      if (!this.handlers.has(type)) this.handlers.set(type, new Set());
      this.handlers.get(type)!.add(handler);
    }
    return () => {
      for (const [type, handler] of entries) {
        this.handlers.get(type)?.delete(handler);
      }
    };
  }
}

export const eventEmitter = new WarpathEventEmitter();
