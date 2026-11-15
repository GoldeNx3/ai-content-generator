"use client";

import { useId, useRef } from "react";
import { XIcon, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Przycisk otwierający okno modalne z natywnym <dialog>: tło, Esc, fokus w oknie.
 * Treść zostaje w drzewie DOM miejsca wywołania (nie w portalu), więc należy do swojej sekcji.
 */
export function InfoDialog({ label, title, icon: Icon, children, className, ...rest }: {
  label: string; title: string; icon?: LucideIcon; children: React.ReactNode; className?: string;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "title" | "children">) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  return (
    <div className={className} {...rest}>
      <button type="button" onClick={() => ref.current?.showModal()}
        className="inline-flex min-h-9 w-full items-center gap-2 rounded-lg px-2 text-left text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
        {Icon && <Icon className="size-4 shrink-0" aria-hidden="true" />}{label}
      </button>
      <dialog ref={ref} aria-labelledby={titleId}
        onClick={(event) => { if (event.target === ref.current) ref.current?.close(); }}
        className={cn("m-auto max-h-[85vh] w-[calc(100%-2rem)] max-w-xl overflow-hidden rounded-2xl bg-card p-0 text-card-foreground shadow-xl ring-1 ring-foreground/10 backdrop:bg-black/40 backdrop:backdrop-blur-[2px]")}>
        <div className="flex max-h-[85vh] flex-col">
          <div className="flex items-start justify-between gap-4 border-b px-5 py-4">
            <h2 id={titleId} className="text-base font-semibold">{title}</h2>
            <button type="button" onClick={() => ref.current?.close()} aria-label="Zamknij okno"
              className="flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
              <XIcon className="size-4" />
            </button>
          </div>
          <div className="overflow-y-auto px-5 py-4">{children}</div>
        </div>
      </dialog>
    </div>
  );
}
