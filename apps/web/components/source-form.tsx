"use client";

import { useState, type FormEvent } from "react";
import { PlusIcon } from "lucide-react";
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
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="grid w-full gap-1.5 sm:w-auto">
        <Label htmlFor="source-name">Nazwa źródła</Label>
        <Input
          id="source-name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="OpenAI"
          className="w-full sm:w-48"
        />
      </div>
      <div className="grid min-w-0 basis-full gap-1.5 sm:min-w-64 sm:flex-1 sm:basis-auto">
        <Label htmlFor="source-url">Adres RSS</Label>
        <Input
          id="source-url"
          type="url"
          required
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://example.com/feed.xml"
        />
      </div>
      <Button type="submit" disabled={saving}>
        <PlusIcon />
        {saving ? "Dodawanie…" : "Dodaj źródło"}
      </Button>
    </form>
  );
}
