"use client";

import { useState, type FormEvent } from "react";
import { Loader2Icon, PlusIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, errorText } from "@/lib/api";

interface ManualSourceFormProps {
  candidateId: number;
  disabled: boolean;
  onAdded: () => void;
}

export function ManualSourceForm({ candidateId, disabled, onAdded }: ManualSourceFormProps) {
  const [url, setUrl] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      const source = await api.addResearchSource(candidateId, url.trim());
      if (source.fetch_status === "success") {
        toast.success("Dodano źródło", { description: "Wybierz „Ponów analizę”, aby uwzględnić je w raporcie." });
      } else {
        toast.warning("Zapisano źródło, ale pobranie treści się nie powiodło", { description: source.error ?? undefined });
      }
      setUrl("");
      onAdded();
    } catch (error) {
      toast.error("Nie udało się dodać źródła", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
      <Input
        type="url"
        required
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="https://… adres dodatkowego źródła"
        aria-label="Adres dodatkowego źródła"
        className="min-w-0 basis-64 flex-1"
        disabled={disabled || saving}
      />
      <Button type="submit" variant="outline" disabled={disabled || saving}>
        {saving ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
        Dodaj źródło
      </Button>
    </form>
  );
}
