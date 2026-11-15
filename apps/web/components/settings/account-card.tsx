"use client";

import { useEffect, useId, useState, type FormEvent } from "react";
import { CheckIcon, EyeIcon, EyeOffIcon, KeyRoundIcon, Loader2Icon, LogOutIcon, UserRoundIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorText } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Me } from "@/types/api";

const MIN_LENGTH = 10;

export function AccountCard() {
  const [me, setMe] = useState<Me | null>(null);
  const [leaving, setLeaving] = useState(false);
  useEffect(() => { api.me().then(setMe, () => setMe(null)); }, []);

  async function logout() {
    setLeaving(true);
    try { await api.logout(); } finally {
      // Pełne przeładowanie zrzuca stan klienta po zmianie sesji.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/login");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><h3 className="flex items-center gap-2 text-lg font-semibold"><UserRoundIcon className="size-5" />Dane konta</h3></CardTitle>
        <CardDescription>Jedno konto to jeden workspace z własnymi źródłami, tematami i budżetem.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid gap-3 sm:grid-cols-2">
          <div className="min-w-0 rounded-lg bg-muted/50 p-3">
            <dt className="text-xs text-muted-foreground">E-mail (login)</dt>
            <dd className="mt-1 flex items-center gap-2 truncate font-medium">
              {me ? <><span aria-hidden="true" className="flex size-6 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-xs font-semibold uppercase text-white">{me.user.email.charAt(0)}</span><span className="truncate">{me.user.email}</span></> : "—"}
            </dd>
          </div>
          <div className="min-w-0 rounded-lg bg-muted/50 p-3">
            <dt className="text-xs text-muted-foreground">Workspace</dt>
            <dd className="mt-1 truncate font-medium">{me ? me.workspace.name : "—"}</dd>
          </div>
        </dl>
        <Button variant="outline" disabled={leaving} onClick={() => void logout()}>
          {leaving ? <Loader2Icon className="animate-spin" /> : <LogOutIcon />} Wyloguj się
        </Button>
      </CardContent>
    </Card>
  );
}

function PasswordInput({ id, label, value, onChange, autoComplete, hint, invalid }: {
  id: string; label: string; value: string; onChange: (value: string) => void; autoComplete: string; hint?: React.ReactNode; invalid?: boolean;
}) {
  const [visible, setVisible] = useState(false);
  const hintId = `${id}-hint`;
  return (
    <div className="grid content-start gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input id={id} type={visible ? "text" : "password"} autoComplete={autoComplete} required value={value} maxLength={1024}
          aria-invalid={invalid || undefined} aria-describedby={hint ? hintId : undefined}
          onChange={(event) => onChange(event.target.value)} className="h-10 pr-10" />
        <button type="button" onClick={() => setVisible((current) => !current)} aria-label={visible ? `Ukryj: ${label}` : `Pokaż: ${label}`}
          className="absolute right-1 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
          {visible ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
        </button>
      </div>
      {hint && <div id={hintId} className="text-xs">{hint}</div>}
    </div>
  );
}

function Rule({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return <li className={cn("flex items-center gap-1.5", ok ? "text-emerald-700" : "text-muted-foreground")}>
    <CheckIcon className={cn("size-3.5", !ok && "opacity-30")} aria-hidden="true" />{children}
    <span className="sr-only">{ok ? " – spełnione" : " – niespełnione"}</span>
  </li>;
}

export function PasswordCard() {
  const formId = useId();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const longEnough = next.length >= MIN_LENGTH;
  const differs = next.length > 0 && next !== current;
  const matches = confirm.length > 0 && next === confirm;
  const valid = current.length > 0 && longEnough && differs && matches;
  const strength = Math.min(4, [next.length >= MIN_LENGTH, next.length >= 16, /[A-Z]/.test(next) && /[a-z]/.test(next), /\d|[^A-Za-z0-9]/.test(next)].filter(Boolean).length);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await api.changePassword({ current_password: current, password: next, password_confirmation: confirm });
      setCurrent(""); setNext(""); setConfirm(""); setDone(true);
      toast.success("Hasło zmienione", { description: "Pozostałe sesje zostały wylogowane." });
    } catch (failure) {
      setError(errorText(failure));
      setDone(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><h3 className="flex items-center gap-2 text-lg font-semibold"><KeyRoundIcon className="size-5" />Zmiana hasła</h3></CardTitle>
        <CardDescription>Po zmianie zostaniesz zalogowany na tym urządzeniu, a pozostałe sesje zostaną zakończone.</CardDescription>
      </CardHeader>
      <CardContent>
        <form id={formId} onSubmit={submit} className="space-y-4" noValidate>
          {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}
          {done && <p role="status" className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">Hasło zmienione. Pozostałe sesje zostały wylogowane.</p>}
          <PasswordInput id="current-password" label="Obecne hasło" autoComplete="current-password" value={current}
            onChange={(value) => { setCurrent(value); setDone(false); }} />
          <div className="grid gap-4 sm:grid-cols-2">
            <PasswordInput id="new-password" label="Nowe hasło" autoComplete="new-password" value={next}
              onChange={(value) => { setNext(value); setDone(false); }}
              hint={<>
                <span className="mb-2 flex gap-1" aria-hidden="true">
                  {[0, 1, 2, 3].map((index) => <span key={index} className={cn("h-1 flex-1 rounded-full", index < strength ? ["bg-rose-400", "bg-amber-400", "bg-emerald-400", "bg-emerald-600"][strength - 1] : "bg-muted")} />)}
                </span>
                <ul className="space-y-0.5">
                  <Rule ok={longEnough}>Co najmniej {MIN_LENGTH} znaków</Rule>
                  <Rule ok={differs}>Inne niż obecne</Rule>
                </ul>
              </>} />
            <PasswordInput id="confirm-password" label="Powtórz nowe hasło" autoComplete="new-password" value={confirm}
              onChange={(value) => { setConfirm(value); setDone(false); }} invalid={confirm.length > 0 && !matches}
              hint={confirm.length > 0 && <ul><Rule ok={matches}>Hasła są takie same</Rule></ul>} />
          </div>
          <Button type="submit" disabled={!valid || saving} className="bg-emerald-700 text-white hover:bg-emerald-800">
            {saving ? <Loader2Icon className="animate-spin" /> : <KeyRoundIcon />} {saving ? "Zmienianie…" : "Zmień hasło"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
