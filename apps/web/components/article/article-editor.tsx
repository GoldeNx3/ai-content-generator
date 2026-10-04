"use client";

import { useId, useState, cloneElement, type ReactElement, type FormEvent } from "react";
import { Loader2Icon, SaveIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { Article, ArticleUpdate } from "@/types/api";

import { Markdown } from "./markdown";

interface ArticleEditorProps {
  article: Article;
  saving: boolean;
  onSave: (data: ArticleUpdate) => void;
  onCancel: () => void;
}

export function ArticleEditor({ article, saving, onSave, onCancel }: ArticleEditorProps) {
  const contentId = useId();
  const [form, setForm] = useState<Required<ArticleUpdate>>({
    title: article.title,
    lead: article.lead,
    content: article.content,
    meta_title: article.meta_title,
    meta_description: article.meta_description,
  });
  const [preview, setPreview] = useState(false);
  const set = (field: keyof ArticleUpdate) => (value: string) => setForm((f) => ({ ...f, [field]: value }));

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const changed = Object.fromEntries(
      Object.entries(form).filter(([key, value]) => value !== article[key as keyof ArticleUpdate]),
    ) as ArticleUpdate;
    onSave(changed);
  }

  return (
    <form onSubmit={handleSubmit} aria-busy={saving}>
      <fieldset disabled={saving} className="space-y-4">
      <Field label="Tytuł" length={form.title.length} max={90}>
        <Input value={form.title} onChange={(e) => set("title")(e.target.value)} required />
      </Field>
      <Field label="Lead">
        <Textarea value={form.lead} onChange={(e) => set("lead")(e.target.value)} rows={3} required />
      </Field>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor={contentId}>Treść (Markdown)</Label>
          <div className="flex gap-1 text-xs">
            {(["Write", "Preview"] as const).map((mode) => (
              <button
                key={mode === "Write" ? "Edytuj" : "Podgląd"}
                type="button"
                aria-pressed={preview === (mode === "Preview")}
                onClick={() => setPreview(mode === "Preview")}
                className={cn(
                  "rounded px-2 py-1",
                  preview === (mode === "Preview") ? "bg-foreground text-background" : "text-muted-foreground",
                )}
              >
                {mode === "Write" ? "Edytuj" : "Podgląd"}
              </button>
            ))}
          </div>
        </div>
        {preview ? (
          <div className="min-h-[28rem] rounded-lg border bg-background px-4 py-2">
            <Markdown>{form.content}</Markdown>
          </div>
        ) : (
          <Textarea
            id={contentId}
            value={form.content}
            onChange={(e) => set("content")(e.target.value)}
            className="min-h-[28rem] font-mono text-sm leading-6"
            required
          />
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Meta title" length={form.meta_title.length} max={60}>
          <Input value={form.meta_title} onChange={(e) => set("meta_title")(e.target.value)} required />
        </Field>
        <Field label="Meta description" length={form.meta_description.length} max={160}>
          <Textarea
            value={form.meta_description}
            onChange={(e) => set("meta_description")(e.target.value)}
            rows={3}
            required
          />
        </Field>
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? <Loader2Icon className="animate-spin" /> : <SaveIcon />}
          Zapisz nową wersję
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={saving}>
          Anuluj
        </Button>
      </div>
      </fieldset>
    </form>
  );
}

function Field({
  label,
  length,
  max,
  children,
}: {
  label: string;
  length?: number;
  max?: number;
  children: React.ReactNode;
}) {
  const id = useId();
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between">
        <Label htmlFor={id}>{label}</Label>
        {length !== undefined && max !== undefined && (
          <span className={cn("text-xs tabular-nums", length > max ? "text-rose-600" : "text-muted-foreground")}>
            {length}/{max}
          </span>
        )}
      </div>
      {cloneElement(children as ReactElement<{id?:string}>, {id})}
    </div>
  );
}
