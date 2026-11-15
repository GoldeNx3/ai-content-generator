"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FlaskConicalIcon, Loader2Icon, RotateCcwIcon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, errorText } from "@/lib/api";

const DEMO_SOURCE = "https://demo.content-engine.invalid/feed.xml";

export function DemoCard() {
  const [hasDemo, setHasDemo] = useState<boolean | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<{ removed: number; created: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSources().then((sources) => setHasDemo(sources.some((source) => source.url === DEMO_SOURCE)), () => setHasDemo(false));
  }, []);

  async function reset() {
    setRunning(true);
    setError(null);
    try {
      const next = await api.resetDemo();
      setResult(next);
      setHasDemo(true);
      setConfirming(false);
      toast.success(`Utworzono ${next.created} tematy demo`);
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setRunning(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><h3 className="flex items-center gap-2 text-lg font-semibold"><FlaskConicalIcon className="size-5" />Tematy demo</h3></CardTitle>
        <CardDescription>Fikcyjne tematy do nauki całego procesu: ocena, research, artykuł, QA, Auto Fix i zatwierdzenie. Działają na prawdziwej kolejce, ale bez AI i internetu — koszt zawsze 0.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-1 text-sm text-muted-foreground">
          <li><span className="font-medium text-foreground">[DEMO 01]</span> cały proces krok po kroku — QA celowo wykryje niepoparte twierdzenie do poprawienia.</li>
          <li><span className="font-medium text-foreground">[DEMO 02]</span> drugi przebieg: nowe wersje, ręczna edycja, historia.</li>
          <li><span className="font-medium text-foreground">[DEMO 03]</span> temat pominięty — decyzja redakcyjna.</li>
        </ul>

        {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}
        {result && <p role="status" className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {result.removed > 0 ? `Usunięto ${result.removed} poprzednie tematy demo razem z ich pracą. ` : ""}Utworzono {result.created} nowe tematy demo.{" "}
          <Link href="/" className="font-medium underline underline-offset-4">Przejdź do tematów</Link> i wybierz źródło „[DEMO]” w filtrze.
        </p>}

        {hasDemo && confirming ? (
          <div role="alertdialog" aria-label="Potwierdź reset tematów demo" className="space-y-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">
            <p>Wszystkie Twoje tematy demo zostaną usunięte razem z ich oceną, researchem, wersjami artykułów, raportami QA i historią zadań, a w ich miejsce powstaną nowe. Prawdziwe tematy nie zostaną zmienione.</p>
            <div className="flex flex-wrap gap-2">
              <Button variant="destructive" disabled={running} onClick={() => void reset()}>
                {running ? <Loader2Icon className="animate-spin" /> : <RotateCcwIcon />}{running ? "Tworzenie…" : "Usuń i utwórz od nowa"}
              </Button>
              <Button variant="ghost" disabled={running} onClick={() => setConfirming(false)}>Anuluj</Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={hasDemo === null || running} onClick={() => hasDemo ? setConfirming(true) : void reset()}>
              {running ? <Loader2Icon className="animate-spin" /> : hasDemo ? <RotateCcwIcon /> : <SparklesIcon />}
              {running ? "Tworzenie…" : hasDemo ? "Zresetuj tematy demo" : "Utwórz tematy demo"}
            </Button>
            <span className="text-xs text-muted-foreground">Bezpłatne · {hasDemo ? "usuwa obecne tematy demo i tworzy nowe" : "dodaje 3 tematy do Twojego konta"}</span>
          </div>
        )}
        {hasDemo && !result && <p className="text-xs text-muted-foreground">Tematy demo już są na Twoim koncie. <Link href="/" className={buttonVariants({ variant: "link", className: "h-auto p-0 text-xs" })}>Otwórz listę tematów</Link></p>}
      </CardContent>
    </Card>
  );
}
