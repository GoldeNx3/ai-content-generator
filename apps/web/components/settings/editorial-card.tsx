"use client";

import { useEffect, useState } from "react";
import { Loader2Icon, PenLineIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, errorText } from "@/lib/api";
import type { EditorialProfile } from "@/types/api";

const EMPTY: EditorialProfile = { audience: "", voice: "", topics_scope: "", banned_phrases: [], example_post: "", style_rules: [] };

export function EditorialCard() {
  const [profile, setProfile] = useState<EditorialProfile | null>(null);
  const [banned, setBanned] = useState("");
  const [rules, setRules] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.editorialProfile().then((loaded) => { setProfile(loaded); setBanned(loaded.banned_phrases.join("\n")); setRules((loaded.style_rules ?? []).join("\n")); }, (err) => setError(errorText(err)));
  }, []);

  const change = (patch: Partial<EditorialProfile>) => { setProfile((current) => ({ ...(current ?? EMPTY), ...patch })); setSaved(false); };

  async function save() {
    if (!profile) return;
    setSaving(true);
    try {
      const next = await api.updateEditorialProfile({ ...profile, banned_phrases: banned.split("\n").map((line) => line.trim()).filter(Boolean),
        style_rules: rules.split("\n").map((line) => line.trim()).filter(Boolean) });
      setProfile(next); setBanned(next.banned_phrases.join("\n")); setRules((next.style_rules ?? []).join("\n")); setSaved(true); setError(null);
    } catch (err) { setError(errorText(err)); }
    finally { setSaving(false); }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><h3 className="flex items-center gap-2 text-lg font-semibold"><PenLineIcon className="size-5" />Profil redakcyjny</h3></CardTitle>
        <CardDescription>Dla kogo i jakim głosem piszesz. Trafia do oceny tematów, briefu, pisania i QA. Puste pola = ogólne zachowanie.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
        {!profile && !error && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2Icon className="size-4 animate-spin" />Wczytywanie…</p>}
        {profile && <>
          <div className="space-y-1">
            <Label htmlFor="ed-audience">Czytelnik</Label>
            <Input id="ed-audience" maxLength={500} placeholder="np. programiści PHP i właściciele małych firm" value={profile.audience} onChange={(e) => change({ audience: e.target.value })} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="ed-voice">Ton i głos</Label>
            <Input id="ed-voice" maxLength={500} placeholder="np. rzeczowo, po koleżeńsku, bez korpomowy" value={profile.voice} onChange={(e) => change({ voice: e.target.value })} />
          </div>
          <div className="space-y-1">
            <Label htmlFor="ed-scope">Zakres tematów</Label>
            <Input id="ed-scope" maxLength={1000} placeholder="np. Laravel, Symfony, DevOps, AI w programowaniu" value={profile.topics_scope} onChange={(e) => change({ topics_scope: e.target.value })} />
            <p className="text-xs text-muted-foreground">Ocena tematów porównuje trafność z tym zakresem.</p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="ed-banned">Zakazane zwroty</Label>
            <Textarea id="ed-banned" rows={3} placeholder={"jeden zwrot w linii, np.\nrewolucja\ngame changer"} value={banned} onChange={(e) => { setBanned(e.target.value); setSaved(false); }} />
            <p className="text-xs text-muted-foreground">Do 50 zwrotów. Pisarz ich unika, a QA i walidacja je zgłaszają.</p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="ed-rules">Zasady stylu</Label>
            <Textarea id="ed-rules" rows={4} placeholder={"jedna zasada w linii, np.\nPierwsze zdanie podaje konkretny fakt z datą."} value={rules} onChange={(e) => { setRules(e.target.value); setSaved(false); }} />
            <p className="text-xs text-muted-foreground">Do 30 zasad (po 200 znaków). Dopisują się też z „Wnioski z Twoich poprawek” na stronie tematu. Pisarz je stosuje, a QA zgłasza naruszenia.</p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="ed-example">Wzorcowy wpis</Label>
            <Textarea id="ed-example" rows={6} maxLength={6000} placeholder="Wklej fragment wpisu, którego styl ma naśladować pisarz (tylko forma, bez faktów)." value={profile.example_post} onChange={(e) => change({ example_post: e.target.value })} />
          </div>
          <div className="flex items-center gap-3">
            <Button disabled={saving} onClick={() => void save()}>{saving ? "Zapisywanie…" : "Zapisz profil"}</Button>
            {saved && <p role="status" className="text-sm text-emerald-700">Profil zapisany.</p>}
          </div>
        </>}
      </CardContent>
    </Card>
  );
}
