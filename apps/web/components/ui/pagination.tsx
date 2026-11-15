"use client";

import { useId } from "react";
import { ChevronLeftIcon, ChevronRightIcon, EllipsisIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { pageCount, pageItems } from "@/lib/pagination";
import { cn } from "@/lib/utils";

export interface PaginationProps {
  /** Bieżąca strona, liczona od 1. */
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  /** Tekst po lewej. Domyślnie „1–25 z 42”. */
  summary?: React.ReactNode;
  /** Wybór liczby pozycji na stronę; pokazywany tylko razem z `onPageSizeChange`. */
  pageSizeOptions?: number[];
  onPageSizeChange?: (pageSize: number) => void;
  /** Liczba numerów stron po każdej stronie bieżącej. */
  siblings?: number;
  disabled?: boolean;
  label?: string;
  className?: string;
}

export function Pagination({
  page, pageSize, total, onPageChange, summary, pageSizeOptions = [10, 25, 50, 100], onPageSizeChange,
  siblings = 1, disabled = false, label = "Paginacja", className,
}: PaginationProps) {
  const sizeLabelId = useId();
  const pages = pageCount(total, pageSize);
  const current = Math.min(Math.max(1, page), pages);
  const from = total === 0 ? 0 : (current - 1) * pageSize + 1;
  const to = Math.min(total, current * pageSize);
  const go = (next: number) => { if (!disabled && next !== current && next >= 1 && next <= pages) onPageChange(next); };

  return (
    <div className={cn("flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground", className)}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <p className="tabular-nums" aria-live="polite">{summary ?? `${from}–${to} z ${total}`}</p>
        {onPageSizeChange && (
          <div className="flex items-center gap-2">
            <span id={sizeLabelId} className="text-xs">Na stronie</span>
            <Select
              disabled={disabled}
              items={pageSizeOptions.map((size) => ({ value: String(size), label: String(size) }))}
              value={String(pageSize)}
              onValueChange={(next) => next !== null && onPageSizeChange(Number(next))}
            >
              <SelectTrigger size="sm" aria-labelledby={sizeLabelId} className="w-18"><SelectValue /></SelectTrigger>
              <SelectContent>
                {pageSizeOptions.map((size) => <SelectItem key={size} value={String(size)}>{size}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <nav aria-label={label} className="flex items-center gap-1">
        <Button variant="outline" size="sm" disabled={disabled || current <= 1} onClick={() => go(current - 1)}>
          <ChevronLeftIcon aria-hidden="true" /><span className="sr-only sm:not-sr-only">Poprzednia</span>
        </Button>

        <ol className="hidden items-center gap-1 sm:flex">
          {pageItems(current, pages, siblings).map((item) => typeof item === "number" ? (
            <li key={item}>
              <Button
                variant={item === current ? "default" : "ghost"}
                size="sm"
                aria-label={`Strona ${item}`}
                aria-current={item === current ? "page" : undefined}
                disabled={disabled}
                onClick={() => go(item)}
                className={cn("min-w-8 justify-center tabular-nums", item === current && "pointer-events-none bg-emerald-700 text-white hover:bg-emerald-700")}
              >
                {item}
              </Button>
            </li>
          ) : (
            <li key={item} aria-hidden="true" className="flex w-8 justify-center text-muted-foreground"><EllipsisIcon className="size-4" /></li>
          ))}
        </ol>
        <span className="px-2 tabular-nums sm:hidden" aria-hidden="true">{current} / {pages}</span>

        <Button variant="outline" size="sm" disabled={disabled || current >= pages} onClick={() => go(current + 1)}>
          <span className="sr-only sm:not-sr-only">Następna</span><ChevronRightIcon aria-hidden="true" />
        </Button>
      </nav>
    </div>
  );
}
