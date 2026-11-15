"use client";

import { useEffect, useRef, useState } from "react";
import { BotIcon, FlaskConicalIcon, PenLineIcon, PlugIcon, UserRoundIcon, WalletIcon, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface SettingsCategory {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

export const SETTINGS_CATEGORIES = [
  { id: "konto", label: "Konto", description: "Dane logowania i hasło", icon: UserRoundIcon },
  { id: "koszty", label: "Budżet i koszty", description: "Zużycie AI w tym miesiącu", icon: WalletIcon },
  { id: "automatyzacja", label: "Automatyzacja", description: "Praca w tle i wstrzymanie", icon: BotIcon },
  { id: "redakcja", label: "Redakcja", description: "Czytelnik, ton i zasady stylu", icon: PenLineIcon },
  { id: "integracje", label: "Integracje", description: "Publikacja w WordPressie", icon: PlugIcon },
  { id: "demo", label: "Tryb demo", description: "Ćwiczenia bez kosztów AI", icon: FlaskConicalIcon },
] as const satisfies readonly SettingsCategory[];

export type SettingsCategoryId = (typeof SETTINGS_CATEGORIES)[number]["id"];

/** Nawigacja po kategoriach: pionowa na desktopie, przewijane „chipsy” na telefonie. Podświetla sekcję w widoku. */
export function SettingsNav() {
  const categories: readonly SettingsCategory[] = SETTINGS_CATEGORIES;
  const [active, setActive] = useState<string>(categories[0].id);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    // Na telefonie lista jest przewijana w poziomie: aktywny chip musi być widoczny.
    const list = listRef.current;
    const link = list?.querySelector<HTMLElement>(`a[href="#${active}"]`);
    if (list && link && list.scrollWidth > list.clientWidth) {
      list.scrollTo({ left: link.offsetLeft - list.clientWidth / 2 + link.offsetWidth / 2, behavior: "smooth" });
    }
  }, [active]);

  useEffect(() => {
    // Aktywna jest ostatnia sekcja, której początek minął górną krawędź (pod przyklejonym nagłówkiem).
    const update = () => {
      const offset = window.innerWidth >= 1024 ? 140 : 200;
      let current = categories[0].id;
      for (const category of categories) {
        const node = document.getElementById(category.id);
        if (node && node.getBoundingClientRect().top <= offset) current = category.id;
      }
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) current = categories[categories.length - 1].id;
      setActive(current);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [categories]);

  return (
    <nav aria-label="Kategorie ustawień" className="-mx-4 bg-zinc-50/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6 lg:mx-0 lg:bg-transparent lg:p-0 lg:backdrop-blur-none">
      <ul ref={listRef} className="relative flex gap-1 overflow-x-auto [scrollbar-width:none] lg:flex-col lg:overflow-visible">
        {categories.map(({ id, label, description, icon: Icon }) => (
          <li key={id} className="shrink-0">
            <a
              href={`#${id}`}
              aria-current={active === id ? "location" : undefined}
              className={cn(
                "flex min-h-10 items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                active === id ? "bg-emerald-50 text-emerald-900 ring-1 ring-emerald-200" : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block font-medium">{label}</span>
                <span className="hidden text-xs text-muted-foreground lg:block">{description}</span>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function SettingsSection({ id, children }: { id: SettingsCategoryId; children: React.ReactNode }) {
  const category: SettingsCategory = SETTINGS_CATEGORIES.find((item) => item.id === id)!;
  const Icon = category.icon;
  return (
    <section id={category.id} aria-labelledby={`${category.id}-heading`} className="scroll-mt-32 space-y-4 lg:scroll-mt-24">
      <div className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200" aria-hidden="true"><Icon className="size-4" /></span>
        <div>
          <h2 id={`${category.id}-heading`} className="text-xl font-semibold tracking-tight">{category.label}</h2>
          <p className="text-sm text-muted-foreground">{category.description}</p>
        </div>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}
