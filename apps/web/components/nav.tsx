"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Tematy" },
  { href: "/sources", label: "Źródła" },
  { href: "/queue", label: "Kolejka" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Nawigacja główna" className="flex min-w-0 gap-1">
      {LINKS.map((link) => {
        const active = link.href === "/" ? pathname === "/" || pathname.startsWith("/candidates") : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={pathname === link.href ? "page" : undefined}
            className={cn(
              "inline-flex min-h-10 items-center rounded-md px-2 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:px-3",
              active ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

const WORKFLOW_LINKS = [
  { href: "#article-workspace", label: "Artykuł" },
  { href: "#workflow-step-1", label: "Temat" },
  { href: "#workflow-step-2", label: "Ocena tematu" },
  { href: "#workflow-step-3", label: "Research" },
  { href: "#workflow-step-4", label: "Generowanie" },
  { href: "#workflow-step-5", label: "QA · jakość" },
  { href: "#workflow-step-6", label: "Poprawki i zatwierdzenie" },
];

export function CandidateScreen({ children }: { children: React.ReactNode }) {
  const [active, setActive] = useState("#article-workspace");
  useEffect(() => {
    const sync = () => {
      const hash = window.location.hash;
      const target = WORKFLOW_LINKS.find(link => link.href === hash)?.href;
      if (target) setActive(target);
      else if (hash.startsWith("#article-")) setActive("#article-workspace");
      if (target?.startsWith("#workflow-step-")) {
        window.dispatchEvent(new Event(`open-${target.slice(1)}`));
      }
    };
    const read = () => setActive("#article-workspace");
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("article-workspace-read", read);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("article-workspace-read", read);
    };
  }, []);
  return <div className="candidate-screen min-w-0 space-y-5" data-view={active.slice(1)}>
    <CandidateNavigation active={active} onSelect={(href) => {
      setActive(href);
      window.dispatchEvent(new Event(`open-${href.slice(1)}`));
      if (href === "#article-workspace") window.dispatchEvent(new Event("article-workspace-read"));
    }} />
    {children}
  </div>;
}

export function CandidateNavigation({ active, onSelect }: { active: string; onSelect: (href: string) => void }) {
  return (
    <nav
      aria-label="Nawigacja po temacie i artykule"
      className="sticky top-14 z-20 min-w-0 max-w-full rounded-xl border bg-background/95 p-1.5 shadow-sm backdrop-blur"
    >
      <div className="flex max-w-full items-center gap-1 overflow-x-auto p-1">
        {WORKFLOW_LINKS.map((link) => (
          <a
            key={link.href}
            href={link.href}
            aria-current={active === link.href ? "location" : undefined}
            onClick={() => onSelect(link.href)}
            className={cn(
              "inline-flex min-h-10 shrink-0 items-center rounded-lg px-3 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              active === link.href
                ? "bg-emerald-700 text-white hover:bg-emerald-800"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {link.label}
          </a>
        ))}
      </div>
    </nav>
  );
}
