"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useState, type FormEvent } from "react";
import { Loader2Icon, SparklesIcon } from "lucide-react";

import { PaidNotice } from "@/components/workflow-step";
import { FilterSelect } from "@/components/filter-select";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FORMAT_OPTIONS, generationDefaults } from "@/lib/article-options";
import {
  type ArticleFormat,
  type ArticleLength,
  type GenerateArticleRequest,
} from "@/types/api";

const LENGTH_OPTIONS: { value: ArticleLength; label: string }[] = [
  { value: "auto", label: "Tyle, ile wymaga temat" },
  { value: "short", label: "Zwięźle — do 400 słów" },
  { value: "long", label: "Długi — pogłębione opracowanie" },
];

interface GenerateArticleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  defaults: GenerateArticleRequest;
  suggestedAngle: string | null;
  refreshTarget?: { title: string; url: string | null } | null;
  busy: boolean;
  onSubmit: (options: GenerateArticleRequest) => void;
}

export function GenerateArticleDialog(props: GenerateArticleDialogProps) {
  // Remount the form on every open so it starts from the latest defaults.
  return (
    <Dialog open={props.open} onOpenChange={(open) => !props.busy && props.onOpenChange(open)}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-lg" showCloseButton={!props.busy}>
        {props.open && <GenerateForm {...props} />}
      </DialogContent>
    </Dialog>
  );
}

function GenerateForm({ title, defaults, suggestedAngle, refreshTarget = null, busy, onSubmit, onOpenChange }: GenerateArticleDialogProps) {
  const demo = useDemoMode();
  const initial = generationDefaults(defaults);
  const [articleFormat, setArticleFormat] = useState<ArticleFormat | "auto">(initial.article_format ?? "auto");
  const [length, setLength] = useState<ArticleLength>(initial.length ?? "auto");
  const [useSuggestedAngle, setUseSuggestedAngle] = useState(!defaults.angle);
  const [angle, setAngle] = useState(defaults.angle ?? "");
  const [instructions, setInstructions] = useState(defaults.instructions ?? "");
  const [refresh, setRefresh] = useState(Boolean(defaults.refresh && refreshTarget));

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      article_format: articleFormat,
      length,
      angle: useSuggestedAngle ? null : angle.trim() || null,
      instructions: instructions.trim() || null,
      refresh: refreshTarget ? refresh : false,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="candidate-form grid gap-5">
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>
          Wybierz, co tekst ma wyjaśnić czytelnikowi. Autor korzysta z faktów z ukończonego researchu.
        </DialogDescription>
      </DialogHeader>

      {demo ? <p className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">Demo: brief i nowa wersja artykułu powstaną bez kosztów AI.</p> : <PaidNotice>Uruchomisz AI do przygotowania briefu i artykułu. Powstanie nowa wersja; poprzednie pozostaną dostępne.</PaidNotice>}

      <div className="grid gap-4 rounded-xl border bg-muted/20 p-4">
        <FilterSelect
          label="Format artykułu"
          allowAll={false}
          value={articleFormat}
          options={FORMAT_OPTIONS}
          onChange={(value) => value && setArticleFormat(value as ArticleFormat | "auto")}
        />
        <p className="text-xs text-muted-foreground">{FORMAT_OPTIONS.find((option) => option.value === articleFormat)?.description}</p>
        <FilterSelect
          label="Długość"
          allowAll={false}
          value={length}
          options={LENGTH_OPTIONS}
          onChange={(value) => value && setLength(value as ArticleLength)}
        />
        <p className="text-xs text-muted-foreground">{length === "long"
          ? "Cel: omówienie 1800–2500 słów, studium przypadku 2200–3000, poradnik lub porównanie 2500–3500, wiadomość 1000–1200. Braki materiału zostaną zgłoszone."
          : length === "short"
            ? "Do 400 słów: sedno tematu i najważniejsze informacje."
            : "Zwykle 1200–1800 słów dla omówienia; długość i plan sekcji są dobierane do tematu oraz źródeł."}</p>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="article-angle">Kąt artykułu — na jakie pytanie odpowiada tekst?</Label>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={useSuggestedAngle}
            onChange={(event) => setUseSuggestedAngle(event.target.checked)}
          />
          <span>
            Przyjmij propozycję researchu
            {suggestedAngle && <span className="mt-0.5 block text-xs text-muted-foreground">{suggestedAngle}</span>}
          </span>
        </label>
        <Textarea
          id="article-angle"
          value={useSuggestedAngle ? suggestedAngle ?? "Perspektywa zostanie dobrana na podstawie researchu." : angle}
          disabled={useSuggestedAngle || busy}
          onChange={(event) => setAngle(event.target.value)}
          placeholder="Jakie pytanie ma wyjaśnić artykuł?"
          maxLength={1000}
          required={!useSuggestedAngle}
        />
      </div>

      <div className="grid gap-2">
        <Label htmlFor="article-instructions">Dodatkowe wskazówki</Label>
        <Textarea
          id="article-instructions"
          value={instructions}
          onChange={(event) => setInstructions(event.target.value)}
          placeholder="Opcjonalnie, np. skup się na decyzjach zespołu i pomiń drugorzędne szczegóły"
          maxLength={2000}
        />
        <p className="text-xs text-muted-foreground">
          Wskazówki wpływają na formę i akcenty. Fakty muszą pochodzić z researchu.
        </p>
      </div>

      {refreshTarget && <div className="grid gap-1 rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-sm">
        <label className="flex items-start gap-2">
          <input type="checkbox" className="mt-1" checked={refresh} disabled={busy} onChange={(event) => setRefresh(event.target.checked)} />
          <span>Napisz jako aktualizację wpisu „{refreshTarget.title}”</span>
        </label>
        <p className="text-xs text-muted-foreground">Autor dostanie treść starego wpisu (pobraną bezpłatnie z WordPressa), zachowa aktualne informacje i pokaże, co się zmieniło. Publikacja utworzy nowy szkic – stary wpis zostaje bez zmian.</p>
      </div>}

      <DialogFooter>
        <Button type="button" variant="outline" disabled={busy} onClick={() => onOpenChange(false)}>Anuluj</Button>
        <Button type="submit" disabled={busy}>
          {busy ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
          {busy ? "Zapisywanie w kolejce…" : demo ? "Generuj · bezpłatne demo" : "Generuj · płatne wywołanie AI"}
        </Button>
      </DialogFooter>
    </form>
  );
}
