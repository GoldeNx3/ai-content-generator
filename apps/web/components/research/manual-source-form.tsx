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
        toast.success("Source added", { description: "Run “Re-run analysis” to include it in the report." });
      } else {
        toast.warning("Source saved, but fetching failed", { description: source.error ?? undefined });
      }
      setUrl("");
      onAdded();
    } catch (error) {
      toast.error("Could not add source", { description: errorText(error) });
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
        placeholder="https://… additional source URL"
        aria-label="Additional source URL"
        className="min-w-64 flex-1"
        disabled={disabled || saving}
      />
      <Button type="submit" variant="outline" disabled={disabled || saving}>
        {saving ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
        Add source
      </Button>
    </form>
  );
}
