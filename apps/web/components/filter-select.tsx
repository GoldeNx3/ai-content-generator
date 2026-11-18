"use client";

import { useId } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ALL = "__all__";

export interface FilterOption {
  value: string;
  label: string;
}

interface FilterSelectProps {
  label: string;
  value: string | undefined;
  options: FilterOption[];
  onChange: (value: string | undefined) => void;
  allowAll?: boolean;
  disabled?: boolean;
  inline?: boolean;
  className?: string;
}

export function FilterSelect({ label, value, options, onChange, allowAll = true, disabled = false, inline = false, className }: FilterSelectProps) {
  const labelId = useId();
  const triggerId = `${labelId}-control`;
  const items = allowAll ? [{ value: ALL, label: "Wszystkie" }, ...options] : options;

  return (
    <div className={inline ? "flex min-w-0 items-center gap-2" : "grid gap-1.5"}>
      <label id={labelId} htmlFor={triggerId} className={inline ? "shrink-0 text-xs font-semibold text-foreground" : "text-xs font-medium text-muted-foreground"}>{label}</label>
    <Select
      disabled={disabled}
      items={items}
      value={value ?? ALL}
      onValueChange={(next) => onChange(next === ALL || next === null ? undefined : String(next))}
    >
      <SelectTrigger id={triggerId} aria-labelledby={labelId} className={className ?? "min-w-36"}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {items.map((item) => (
          <SelectItem key={item.value} value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
    </div>
  );
}
