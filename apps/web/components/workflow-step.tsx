import { cn } from "@/lib/utils";

export function WorkflowStep({ number, title, status, paid, children }: {
  number: number; title: string; status: string; paid: boolean; children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border bg-card p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold"><span className="mr-2 text-muted-foreground">{number}.</span>{title}</h2>
        <span className={cn("rounded-full px-2 py-1 text-xs font-medium", paid ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900")}>
          {paid ? "Płatne · AI" : "Bez kosztu AI"}
        </span>
      </div>
      <p className="text-sm font-medium" role="status" aria-live="polite">{status}</p>
      <div className="text-sm text-muted-foreground">{children}</div>
    </section>
  );
}

export function PaidNotice({ children }: { children?: React.ReactNode }) {
  return <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
    <p className="font-semibold">Płatne wywołanie AI · każde uruchomienie nalicza nowy koszt</p>
    <p className="mt-1">Cena zależy od modelu i liczby tokenów. Wycena przed uruchomieniem nie jest dostępna.</p>
    {children && <p className="mt-1">{children}</p>}
  </div>;
}
