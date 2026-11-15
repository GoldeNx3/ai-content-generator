"use client";

import { createContext, useContext } from "react";

const DemoContext = createContext(false);
export const DemoModeProvider = DemoContext.Provider;
export const useDemoMode = () => useContext(DemoContext);

/** Informacja o trybie demo. Opis etapów jest w oknie „Jak działa ten etap?” każdego etapu. */
export function DemoNotice() {
  return (
    <p className="rounded-lg bg-sky-50 px-4 py-3 text-sm text-sky-900 ring-1 ring-sky-200">
      <strong>Tryb demo · 0 kosztów AI.</strong> Fikcyjne dane i symulowane odpowiedzi — akcje używają kolejki i workera, ale bez AI i internetu.
      Pełny katalog scenariuszy: <code>docs/demo/README.md</code>.
    </p>
  );
}
