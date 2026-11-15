"use client";

import { useState, type FormEvent } from "react";
import { Loader2Icon, PlusIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorText } from "@/lib/api";

export function SourceForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      const source = await api.createSource({ name: name.trim(), url: url.trim() });
      toast.success(`Dodano źródło: ${source.name}`);
      setName("");
      setUrl("");
      onCreated();
    } catch (error) {
      toast.error("Nie udało się dodać źródła", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_auto] sm:items-end">
      <div className="grid min-w-0 gap-1.5">
        <Label htmlFor="source-name">Nazwa źródła</Label>
        <Input
          id="source-name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="np. OpenAI Blog"
          className="h-10"
        />
      </div>
      <div className="grid min-w-0 gap-1.5">
        <Label htmlFor="source-url">Adres RSS</Label>
        <Input
          id="source-url"
          type="url"
          required
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://example.com/feed.xml"
          className="h-10 font-mono text-sm"
        />
      </div>
      <Button type="submit" size="lg" disabled={saving} className="h-10 bg-emerald-700 text-white hover:bg-emerald-800">
        {saving ? <Loader2Icon className="animate-spin" /> : <PlusIcon />}
        {saving ? "Dodawanie…" : "Dodaj źródło"}
      </Button>
    </form>
  );
}
