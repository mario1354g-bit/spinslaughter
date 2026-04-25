import type { BookEvent } from '$lib/game/types';

export const events: Partial<Record<BookEvent['type'], BookEvent>> = {};
