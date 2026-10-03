"use client";

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
import {
  CANDIDATE_CATEGORIES,
  type ArticleLength,
  type CandidateCategory,
  type GenerateArticleRequest,
} from "@/types/api";

const LENGTH_OPTIONS: { value: ArticleLength; label: string }[] = [
  { value: "auto", label: "Length: Auto" },
  { value: "short", label: "Length: Short" },
  { value: "standard", label: "Length: Standard" },
  { value: "long", label: "Length: Long" },
];

interface GenerateArticleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  defaults: GenerateArticleRequest;
  defaultType: CandidateCategory;
  suggestedAngle: string | null;
  busy: boolean;
  onSubmit: (options: GenerateArticleRequest) => void;
}

export function GenerateArticleDialog(props: GenerateArticleDialogProps) {
  // Remount the form on every open so it starts from the latest defaults.
  return (
    <Dialog open={props.open} onOpenChange={(open) => !props.busy && props.onOpenChange(open)}>
      <DialogContent className="sm:max-w-lg" showCloseButton={!props.busy}>
        {props.open && <GenerateForm {...props} />}
      </DialogContent>
    </Dialog>
  );
}

function GenerateForm({ title, defaults, defaultType, suggestedAngle, busy, onSubmit }: GenerateArticleDialogProps) {
  const [articleType, setArticleType] = useState<CandidateCategory>(defaults.article_type ?? defaultType);
  const [length, setLength] = useState<ArticleLength>(defaults.length ?? "auto");
  const [useSuggestedAngle, setUseSuggestedAngle] = useState(!defaults.angle);
  const [angle, setAngle] = useState(defaults.angle ?? "");
  const [instructions, setInstructions] = useState(defaults.instructions ?? "");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit({
      article_type: articleType,
      length,
      angle: useSuggestedAngle ? null : angle.trim() || null,
      instructions: instructions.trim() || null,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>
          The writer uses only facts from the completed research. A new version is created; older drafts stay.
        </DialogDescription>
      </DialogHeader>

      <PaidNotice>Uruchomisz AI do przygotowania briefu i artykułu. Powstanie nowa wersja; poprzednie pozostaną dostępne.</PaidNotice>

      <div className="flex flex-wrap gap-2">
        <FilterSelect
          label="Article type"
          allowAll={false}
          value={articleType}
          options={CANDIDATE_CATEGORIES.map((value) => ({ value, label: `Type: ${value}` }))}
          onChange={(value) => value && setArticleType(value as CandidateCategory)}
        />
        <FilterSelect
          label="Length"
          allowAll={false}
          value={length}
          options={LENGTH_OPTIONS}
          onChange={(value) => value && setLength(value as ArticleLength)}
        />
      </div>

      <div className="grid gap-2">
        <Label>Angle</Label>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={useSuggestedAngle}
            onChange={(event) => setUseSuggestedAngle(event.target.checked)}
          />
          <span>
            Use research suggestion
            {suggestedAngle && <span className="mt-0.5 block text-xs text-muted-foreground">{suggestedAngle}</span>}
          </span>
        </label>
        {!useSuggestedAngle && (
          <Textarea
            value={angle}
            onChange={(event) => setAngle(event.target.value)}
            placeholder="Your angle for this article"
            maxLength={1000}
            required
          />
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="article-instructions">Additional instructions</Label>
        <Textarea
          id="article-instructions"
          value={instructions}
          onChange={(event) => setInstructions(event.target.value)}
          placeholder="Optional, e.g. focus on what this means for developers"
          maxLength={2000}
        />
        <p className="text-xs text-muted-foreground">
          Instructions shape form and focus. They can’t add facts — content comes only from the research.
        </p>
      </div>

      <DialogFooter>
        <Button type="submit" disabled={busy}>
          {busy ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
          {busy ? "Generating… (brief + draft, up to ~1 min)" : "Generuj · płatne wywołanie AI"}
        </Button>
      </DialogFooter>
    </form>
  );
}
