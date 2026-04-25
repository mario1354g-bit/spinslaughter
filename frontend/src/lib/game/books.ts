import { BOOK_PATH } from './constants';
import type { Book } from './types';

export type BookMode = 'base' | 'warpath_buy_8' | 'warpath_buy_10' | 'warpath_buy_12';

export const BOOK_MODE_COSTS: Record<BookMode, number> = {
  base: 1,
  warpath_buy_8: 80,
  warpath_buy_10: 100,
  warpath_buy_12: 120
};

const cache = new Map<BookMode, Book[]>();
const weightedCache = new Map<BookMode, { book: Book; weight: number }[]>();

export async function loadBooks(mode: BookMode): Promise<Book[]> {
  if (cache.has(mode)) return cache.get(mode)!;
  const response = await fetch(`${BOOK_PATH}/books_${mode}.jsonl`);
  if (!response.ok) throw new Error(`Unable to load books for ${mode}`);
  const text = await response.text();
  const books = text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as Book);
  cache.set(mode, books);
  return books;
}

async function loadWeightedBooks(mode: BookMode): Promise<{ book: Book; weight: number }[]> {
  if (weightedCache.has(mode)) return weightedCache.get(mode)!;
  const books = await loadBooks(mode);
  const byId = new Map(books.map((book) => [book.id, book]));
  try {
    const response = await fetch(`${BOOK_PATH}/lookUpTable_${mode}.csv`);
    if (!response.ok) throw new Error(`Unable to load lookup table for ${mode}`);
    const text = await response.text();
    const rows = text
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    const dataRows = rows[0]?.toLowerCase().startsWith('id,') ? rows.slice(1) : rows;
    const weighted = dataRows
      .map((line) => {
        const [id, weight] = line.split(',');
        const book = byId.get(Number(id));
        return book ? { book, weight: Number(weight) || 0 } : undefined;
      })
      .filter((entry): entry is { book: Book; weight: number } => Boolean(entry && entry.weight > 0));
    if (weighted.length > 0) {
      weightedCache.set(mode, weighted);
      return weighted;
    }
  } catch (error) {
    console.warn(error);
  }
  const fallback = books.map((book) => ({ book, weight: 1 }));
  weightedCache.set(mode, fallback);
  return fallback;
}

export async function pickBook(mode: BookMode): Promise<Book> {
  const weightedBooks = await loadWeightedBooks(mode);
  const totalWeight = weightedBooks.reduce((sum, entry) => sum + entry.weight, 0);
  let roll = Math.random() * totalWeight;
  for (const entry of weightedBooks) {
    roll -= entry.weight;
    if (roll <= 0) return entry.book;
  }
  return weightedBooks[weightedBooks.length - 1].book;
}
