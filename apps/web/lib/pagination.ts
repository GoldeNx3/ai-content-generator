export type PageItem = number | "ellipsis-start" | "ellipsis-end";

export function pageCount(total: number, pageSize: number): number {
  return Math.max(1, Math.ceil(total / Math.max(1, pageSize)));
}

/**
 * Numery stron do wyświetlenia. Zawsze pierwsza i ostatnia, `siblings` wokół bieżącej, luki jako elipsa.
 * Liczba pozycji jest stała (siblings * 2 + 5), więc kontrolka nie „skacze” przy zmianie strony.
 */
export function pageItems(current: number, pages: number, siblings = 1): PageItem[] {
  if (pages <= siblings * 2 + 5) return Array.from({ length: pages }, (_, index) => index + 1);
  const page = Math.min(Math.max(1, current), pages);
  const start = Math.max(Math.min(page - siblings, pages - siblings * 2 - 2), 3);
  const end = Math.min(Math.max(page + siblings, siblings * 2 + 3), pages - 2);
  const middle = Array.from({ length: end - start + 1 }, (_, index) => start + index);
  return [1, start > 3 ? "ellipsis-start" : 2, ...middle, end < pages - 2 ? "ellipsis-end" : pages - 1, pages];
}

/** Polska odmiana: 1 temat, 2 tematy, 5 tematów, 22 tematy. */
export function plural(count: number, one: string, few: string, many: string): string {
  if (count === 1) return one;
  const mod10 = count % 10;
  const mod100 = count % 100;
  return mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? few : many;
}
