"use client";

import { createContext, useContext } from "react";

const DemoContext = createContext(false);
export const DemoModeProvider = DemoContext.Provider;
export const useDemoMode = () => useContext(DemoContext);

export function PipelineGuide({ demo }: { demo: boolean }) {
  return <div className="space-y-3">
    {demo && <p className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900"><strong>Tryb demo · 0 kosztów AI.</strong> Fikcyjne dane i symulowane odpowiedzi. Instrukcję wszystkich etapów znajdziesz poniżej.</p>}
    <details className="rounded-xl border bg-card p-4 shadow-sm">
    <summary className="cursor-pointer rounded-sm text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring">Jak działa pipeline i kiedy dostępny jest Auto Fix?</summary>
    <div className="mt-4 space-y-4 text-sm leading-relaxed text-muted-foreground">
      {demo && <p className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sky-900">Dane Nexa są fikcyjne. Klikane akcje używają kolejki i workera z symulowanymi odpowiedziami, bez AI i internetu. Scenariusz 01 pozwala przejść cały flow. Scenariusze opisane jako „migawka” pokazują nieruchome stany queued/running.</p>}
      <ol className="list-decimal space-y-2 pl-5">
        <li><strong className="text-foreground">Discover:</strong> zapisuje temat z RSS. W demo temat dostarcza seeder. Nie tworzy artykułu.</li>
        <li><strong className="text-foreground">Classify:</strong> ocenia temat i przypisuje kategorię. Punktacja pomaga w wyborze; nie jest warunkiem uruchomienia Research. Zatwierdzenie tematu jest osobną decyzją od approval tekstu.</li>
        <li><strong className="text-foreground">Research:</strong> zbiera dowody, fakty, źródła, niepewności i konflikty. Generowanie tekstu wymaga ukończonego Research z faktami.</li>
        <li><strong className="text-foreground">Brief:</strong> wybiera kąt, odbiorcę, fakty i plan sekcji. Brief oraz Write uruchamiają się razem w karcie generowania.</li>
        <li><strong className="text-foreground">Write:</strong> tworzy nową wersję artykułu ze snapshotem Research. Wybór wersji w QA określa dokładnie analizowany tekst; wygenerowanie wersji nie oznacza jej zatwierdzenia.</li>
        <li><strong className="text-foreground">QA:</strong> sprawdza tekst, referencje, styl, strukturę i SEO wyłącznie względem zapisanych dowodów. Backend liczy score. QA passed wymaga wyniku co najmniej progu raportu, zero critical oraz zero unsupported.</li>
        <li><strong className="text-foreground">Auto Fix + Approval:</strong> Auto Fix wymaga aktualnego, ukończonego QA, problemów auto-fixable, wolnej kolejki i pozostałej iteracji. Niepewnych danych i konfliktów nie rozstrzyga przez zgadywanie. Tworzy nową wersję; jej QA uruchamiasz osobno. Approval dotyczy konkretnej wersji z ważnym QA passed; niczego nie publikuje.</li>
      </ol>
      <p><strong className="text-foreground">Dlaczego przycisk jest wyłączony?</strong> Sprawdź status zadania, aktualność raportu, liczbę auto-fixable issues i pozostałe iteracje. Niski score sam nie uruchamia Auto Fix. Warnings mogą pozostać przy approval, ale critical i unsupported je blokują. Każda ręczna zmiana tworzy nową wersję wymagającą QA.</p>
      <p>Queued → running → succeeded oznacza wykonanie zadania, a nie zatwierdzenie artykułu. Failed pozwala na retry. Jeden Auto Fix wykonuje jedną iterację; kolejna wymaga kliknięcia. Po wyczerpaniu limitu i nieudanym QA potrzebna jest ręczna weryfikacja.</p>
      {demo && <p>Pełna instrukcja i katalog scenariuszy: <code>docs/demo/README.md</code>. Ponowne <code>make seed-demo</code> dopisuje brakujące przypadki; zachowuje dotychczasowe kliknięcia oraz prawdziwe dane.</p>}
    </div>
  </details>
  </div>;
}
