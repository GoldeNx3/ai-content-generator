import { cn } from "@/lib/utils";

export function PageHeader({ eyebrow, title, description, actions, actionsNote, className }: {
  eyebrow?: string;
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  /** Krótka linia pod przyciskami, np. status akcji (ogłaszana czytnikom). */
  actionsNote?: React.ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="min-w-0 space-y-1">
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">{eyebrow}</p>}
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="max-w-2xl text-sm text-muted-foreground">{description}</p>}
      </div>
      {(actions || actionsNote) && (
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:items-end">
          {actions && <div className="flex flex-wrap gap-2 [&>*]:flex-1 sm:[&>*]:flex-none">{actions}</div>}
          {actionsNote && <p className="text-xs text-muted-foreground" role="status" aria-live="polite">{actionsNote}</p>}
        </div>
      )}
    </header>
  );
}
