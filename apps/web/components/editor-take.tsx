"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, errorText } from "@/lib/api";
import type { Candidate } from "@/types/api";

// Darmowe pole przed krokiem 4: opinia i doświadczenie redakcji trafiają do briefu i pisarza jako „Nasze zdanie”.
export function EditorTake({ candidate, onSaved }: { candidate: Candidate; onSaved: (candidate: Candidate) => void }) {
  const [value, setValue] = useState(candidate.editor_take ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    try { onSaved(await api.updateEditorTake(candidate.id, value.trim() || null)); setSaved(true); setError(null); }
    catch (err) { setError(errorText(err)); }
    finally { setSaving(false); }
  }

  return (
    <div className="space-y-2">
      <Label htmlFor="editor-take" className="text-sm font-medium">Nasze zdanie (opcjonalnie)</Label>
      <p id="editor-take-help" className="text-xs text-muted-foreground">Pisarz doda go jako wyraźnie oznaczony komentarz — to jedyne miejsce, z którego wolno mu wziąć opinię.</p>
      <Textarea id="editor-take" aria-describedby="editor-take-help" rows={4} maxLength={3000} placeholder="np. Używamy tego w projektach klientów; największy problem to…" value={value}
        onChange={(event) => { setValue(event.target.value); setSaved(false); }} />
      <div className="flex items-center gap-3">
        <Button size="sm" variant="outline" disabled={saving || value.trim() === (candidate.editor_take ?? "")} onClick={() => void save()}>{saving ? "Zapisywanie…" : "Zapisz komentarz · bezpłatne"}</Button>
        {saved && <p role="status" className="text-sm text-emerald-700">Komentarz zapisany.</p>}
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      </div>
    </div>
  );
}
