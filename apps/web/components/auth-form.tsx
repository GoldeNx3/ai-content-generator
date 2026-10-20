"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Loader2Icon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorText } from "@/lib/api";

// Powrót tylko na ścieżkę w tej aplikacji: "//evil.com" lub pełny URL to open redirect.
export function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\") ? value : "/";
}

const COPY = {
  login: { title: "Zaloguj się", description: "Dostęp do panelu Content Engine.", submit: "Zaloguj", switchText: "Nie masz konta?", switchLabel: "Zarejestruj się", switchHref: "/register" },
  register: { title: "Załóż konto", description: "Hasło musi mieć co najmniej 10 znaków.", submit: "Utwórz konto", switchText: "Masz już konto?", switchLabel: "Zaloguj się", switchHref: "/login" },
} as const;

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const copy = COPY[mode];
  const next = safeNext(useSearchParams().get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Ważna sesja (np. otwarty /login w nowej karcie) - od razu do panelu. Nieważne ciasteczko zostaje
  // tu bez przekierowania, więc nie powstaje pętla /login <-> /.
  useEffect(() => {
    api.me().then(() => window.location.replace(next), () => undefined);
  }, [next]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const credentials = { email: email.trim(), password };
      await (mode === "login" ? api.login(credentials) : api.register(credentials));
      // Pełne przeładowanie: proxy.ts i wszystkie strony widzą świeże ciasteczko sesji.
      window.location.assign(next);
    } catch (err) {
      setError(errorText(err));
      setSubmitting(false);
    }
  }

  const switchHref = next === "/" ? copy.switchHref : `${copy.switchHref}?next=${encodeURIComponent(next)}`;
  return (
    <div className="mx-auto flex w-full max-w-sm flex-col pt-8 sm:pt-16">
      <Card>
        <CardHeader>
          <CardTitle><h1 className="text-xl font-semibold">{copy.title}</h1></CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="auth-email">Email</Label>
              <Input id="auth-email" type="email" autoComplete="email" required value={email}
                onChange={(event) => setEmail(event.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="auth-password">Hasło</Label>
              <Input id="auth-password" type="password" required minLength={mode === "register" ? 10 : undefined}
                autoComplete={mode === "login" ? "current-password" : "new-password"} value={password}
                onChange={(event) => setPassword(event.target.value)} />
            </div>
            {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}
            <Button type="submit" disabled={submitting} className="min-h-10">
              {submitting && <Loader2Icon className="size-4 animate-spin" />}
              {copy.submit}
            </Button>
          </form>
          <p className="mt-4 text-sm text-muted-foreground">
            {copy.switchText}{" "}
            <Link href={switchHref} className="font-medium text-foreground underline underline-offset-4">{copy.switchLabel}</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
