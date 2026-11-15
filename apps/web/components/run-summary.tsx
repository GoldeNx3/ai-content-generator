import { CircleAlertIcon, CircleCheckIcon, XIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface RunSummaryLine {
  text: string;
  failed?: boolean;
}

/** Karta z wynikami ręcznie uruchomionych akcji (pobieranie RSS, zlecenie oceny…). */
export function RunSummary({ title, lines, onClear }: { title: string; lines: RunSummaryLine[]; onClear?: () => void }) {
  if (lines.length === 0) return null;
  return (
    <div className="flex gap-3 rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/8" role="status" aria-live="polite">
      <div className="min-w-0 flex-1 space-y-2">
        <p className="text-sm font-semibold">{title}</p>
        {lines.map(({ text, failed }) => {
          const Icon = failed ? CircleAlertIcon : CircleCheckIcon;
          return <p key={text} className={cn("flex items-start gap-2 text-sm", failed ? "text-rose-800" : "text-foreground")}>
            <Icon className={cn("mt-0.5 size-4 shrink-0", failed ? "text-rose-600" : "text-emerald-600")} aria-hidden="true" />{text}
          </p>;
        })}
      </div>
      {onClear && <Button variant="ghost" size="icon-sm" aria-label="Wyczyść wyniki" title="Wyczyść" onClick={onClear}><XIcon /></Button>}
    </div>
  );
}
