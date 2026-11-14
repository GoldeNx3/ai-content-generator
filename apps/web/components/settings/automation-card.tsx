"use client";

import { useEffect, useState } from "react";
import { Loader2Icon, PauseCircleIcon, PlayCircleIcon, TimerIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { AUTOMATION_INTERVALS, type AutomationSettings, type AutomationUpdate } from "@/types/api";

const INTERVAL_LABELS: Record<number, string> = {
  15: "co 15 minut", 30: "co 30 minut", 60: "co godzinę", 120: "co 2 godziny", 360: "co 6 godzin", 720: "co 12 godzin", 1440: "raz na dobę",
};

export function AutomationCard() {
  const [settings, setSettings] = useState<AutomationSettings | null>(null);
  const [limit, setLimit] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.automation().then((loaded) => { setSettings(loaded); setLimit(String(loaded.auto_classify_batch_limit)); }, (err) => setError(errorText(err)));
  }, []);

  async function save(change: AutomationUpdate) {
    const previous = settings;
    // Optymistycznie: kontrolka zmienia się od razu, błąd zapisu przywraca poprzedni stan.
    setSettings((current) => current && { ...current, ...change });
    setSaving(true);
    try {
      const next = await api.updateAutomation(change);
      setSettings(next); setLimit(String(next.auto_classify_batch_limit)); setError(null);
    } catch (err) {
      setSettings(previous); if (previous) setLimit(String(previous.auto_classify_batch_limit)); setError(errorText(err));
    }
    finally { setSaving(false); }
  }

  async function togglePause() {
    if (!settings) return;
    setSaving(true);
    try {
      if (settings.paused_at) await api.resumeWorkspace(); else await api.pauseWorkspace();
      setSettings(await api.automation()); setError(null);
    } catch (err) { setError(errorText(err)); }
    finally { setSaving(false); }
  }

  const locked = !settings?.can_edit || saving;
  const run = settings?.last_auto_run_result;

  return (
    <Card>
      <CardHeader>
        <CardTitle><h2 className="flex items-center gap-2 text-lg font-semibold"><TimerIcon className="size-5" />Automatyka</h2></CardTitle>
        <CardDescription>Co ten workspace robi sam w tle. Domyślnie nic: pobieranie i ocenę zlecasz ręcznie.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
        {!settings && !error && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2Icon className="size-4 animate-spin" />Wczytywanie…</p>}
        {settings && <>
          {!settings.automation_enabled_globally && <p role="status" className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">Administrator wyłączył automatykę dla całej instancji (AUTOMATION_ENABLED=false). Ustawienia zadziałają po jej włączeniu.</p>}
          {!settings.can_edit && <p className="text-sm text-muted-foreground">Zmieniać może tylko właściciel workspace&apos;u.</p>}

          <div className="flex flex-wrap items-center gap-3">
            <input id="auto-fetch" type="checkbox" className="size-4" checked={settings.auto_fetch_enabled} disabled={locked}
              onChange={(event) => void save({ auto_fetch_enabled: event.target.checked })} />
            <Label htmlFor="auto-fetch">Automatycznie pobieraj RSS (bezpłatne)</Label>
            <select id="auto-interval" aria-label="Częstotliwość pobierania" className="h-9 rounded-md border bg-background px-3 text-sm"
              value={settings.auto_fetch_interval_minutes} disabled={locked}
              onChange={(event) => void save({ auto_fetch_interval_minutes: Number(event.target.value) })}>
              {AUTOMATION_INTERVALS.map((minutes) => <option key={minutes} value={minutes}>{INTERVAL_LABELS[minutes]}</option>)}
            </select>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <input id="auto-classify" type="checkbox" className="size-4" checked={settings.auto_classify_enabled} disabled={locked}
                onChange={(event) => void save({ auto_classify_enabled: event.target.checked })} />
              <Label htmlFor="auto-classify">Po pobraniu od razu zlecaj ocenę nowych tematów · płatne (OpenAI)</Label>
            </div>
            <div className="flex items-center gap-3 pl-7">
              <Label htmlFor="auto-limit" className="text-sm font-normal text-muted-foreground">Najwyżej ocen na przebieg</Label>
              <Input id="auto-limit" type="number" min={1} max={200} className="w-24" value={limit} disabled={locked}
                onChange={(event) => setLimit(event.target.value)}
                onBlur={() => { const value = Number(limit); if (value !== settings.auto_classify_batch_limit) void save({ auto_classify_batch_limit: value }); }} />
            </div>
            <p className="pl-7 text-xs text-muted-foreground">Ten sam limit obowiązuje przy „oceń oczekujące” i przy ręcznym make pipeline. Budżet miesięczny dalej obowiązuje.</p>
          </div>

          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Ostatni przebieg</dt>
            <dd>{settings.last_auto_run_at ? formatDate(settings.last_auto_run_at) : "jeszcze nie było"}
              {run && ` · nowe tematy ${run.new_candidates} · zlecone oceny ${run.enqueued}${run.errors ? ` · błędy źródeł ${run.errors}` : ""}${run.budget_exceeded ? " · budżet wyczerpany" : ""}`}</dd>
            <dt className="text-muted-foreground">Następny</dt>
            <dd>{settings.next_auto_run_at ? formatDate(settings.next_auto_run_at) : settings.paused_at ? "wstrzymane" : "wyłączone"}</dd>
          </dl>

          <div className="space-y-2 border-t pt-4">
            {settings.paused_at
              ? <p role="status" className="text-sm text-amber-900">Workspace wstrzymany od {formatDate(settings.paused_at)}: worker nie bierze jego zadań, automatyka stoi, nowe zadania nie są przyjmowane.</p>
              : <p className="text-sm text-muted-foreground">Wstrzymanie zatrzymuje wszystkie zadania tego workspace&apos;u (także publikację). Trwające zadanie dokończy bieżący krok.</p>}
            {settings.can_edit && <Button variant={settings.paused_at ? "default" : "outline"} disabled={saving} onClick={() => void togglePause()}>
              {settings.paused_at ? <><PlayCircleIcon />Wznów workspace</> : <><PauseCircleIcon />Wstrzymaj workspace</>}
            </Button>}
          </div>
        </>}
      </CardContent>
    </Card>
  );
}
