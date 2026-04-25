import { bookEventHandlerMap, type BookEventContext } from './bookEventHandlers';
import type { Book, BookEvent } from './types';

export async function playBookEvent(event: BookEvent, context: BookEventContext): Promise<void> {
  const handler = bookEventHandlerMap[event.type] as ((event: BookEvent, context: BookEventContext) => Promise<void> | void) | undefined;
  if (!handler) {
    console.warn(`[Warpath] No handler for book event ${event.type}`);
    return;
  }
  await handler(event, context);
}

export async function playBookEvents(book: Book): Promise<void> {
  const context = { bookEvents: book.events };
  for (const event of book.events) {
    await playBookEvent(event, context);
  }
}
