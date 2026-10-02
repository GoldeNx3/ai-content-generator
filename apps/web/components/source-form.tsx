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
      toast.success(`Added ${source.name}`);
      setName("");
      setUrl("");
      onCreated();
    } catch (error) {
      toast.error("Could not add source", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="grid gap-1.5">
        <Label htmlFor="source-name">Name</Label>
        <Input
          id="source-name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="OpenAI"
          className="w-48"
        />
      </div>
      <div className="grid min-w-64 flex-1 gap-1.5">
        <Label htmlFor="source-url">RSS URL</Label>
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
        Add source
      </Button>
    </form>
  );
}
