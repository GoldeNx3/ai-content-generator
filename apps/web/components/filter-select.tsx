"use client";

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
}

export function FilterSelect({ label, value, options, onChange, allowAll = true }: FilterSelectProps) {
  const items = allowAll ? [{ value: ALL, label: `All ${label.toLowerCase()}` }, ...options] : options;

  return (
    <Select
      items={items}
      value={value ?? ALL}
      onValueChange={(next) => onChange(next === ALL || next === null ? undefined : String(next))}
    >
      <SelectTrigger aria-label={label} className="min-w-36">
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
  );
}
