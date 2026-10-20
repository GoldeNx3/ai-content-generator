"use client";

import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2Icon, ExternalLinkIcon, Loader2Icon, PlugIcon, TriangleAlertIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, api, errorText, WORDPRESS_MESSAGES } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { WordPressConnection } from "@/types/api";

const SEO_LABELS: Record<WordPressConnection["seo_plugin"], string> = { yoast: "Yoast SEO", rankmath: "Rank Math", none: "brak" };
const STATUS_LABELS: Record<WordPressConnection["default_status"], string> = { draft: "Szkic", future: "Zaplanowany", publish: "Opublikowany" };

type Busy = "load" | "authorize" | "manual" | "test" | "disconnect" | "defaults" | null;

export function WordPressConnectionCard() {
  const [connection, setConnection] = useState<WordPressConnection | null>(null);
  const [busy, setBusy] = useState<Busy>("load");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    api.wordpressConnection()
      .then(setConnection, (err) => setError(errorText(err)))
      .finally(() => setBusy(null));
  }, []);

  async function run(kind: Busy, action: () => Promise<void>) {
    setBusy(kind);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(null);
    }
  }

  if (busy === "load") {
    return <Card><CardContent className="flex items-center gap-2 py-8 text-sm text-muted-foreground"><Loader2Icon className="size-4 animate-spin" />Wczytywanie połączenia…</CardContent></Card>;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle><h2 className="flex items-center gap-2 text-lg font-semibold"><PlugIcon className="size-5" />WordPress</h2></CardTitle>
        <CardDescription>Strona, na którą trafiają artykuły tego workspace&apos;u. Jedna strona na workspace.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}
        {connection && !editing ? (
          <ConnectedView connection={connection} busy={busy}
            onTest={() => run("test", async () => {
              const result = await api.testWordPressConnection();
              setConnection(result);
              if (result.last_error) setError(WORDPRESS_MESSAGES[result.last_error] ?? result.last_error);
              else toast.success("Połączenie z WordPressem działa");
            })}
            onDefaults={(values) => run("defaults", async () => {
              setConnection(await api.updateWordPressDefaults(values));
              toast.success("Zapisano ustawienia publikacji");
            })}
            onChange={() => setEditing(true)}
            onDisconnect={() => run("disconnect", async () => {
              await api.disconnectWordPress();
              setConnection(null);
              toast.success("Rozłączono WordPressa");
            })} />
        ) : (
          <ConnectForm current={connection} busy={busy} onCancel={connection ? () => setEditing(false) : undefined}
            onAuthorize={(site_url, api_url) => run("authorize", async () => {
              const { authorize_url } = await api.authorizeWordPress({ site_url, api_url });
              // Pełne przejście do WordPressa; wracamy na /settings/wordpress/callback.
              window.location.assign(authorize_url);
            })}
            onManual={(body) => run("manual", async () => {
              try {
                setConnection(await api.connectWordPress(body));
              } catch (err) {
                if (err instanceof ApiError && err.detail?.code === "wordpress_site_change_requires_confirmation"
                    && window.confirm("Wpisy opublikowane na obecnej stronie zostaną odpięte, a artykuły trafią na nową stronę jako nowe szkice. Zmienić stronę?")) {
                  setConnection(await api.connectWordPress({ ...body, confirm_site_change: true }));
                } else {
                  throw err;
                }
              }
              setEditing(false);
              toast.success("Połączono z WordPressem");
            })} />
        )}
        <BridgeHelp />
      </CardContent>
    </Card>
  );
}

function ConnectedView({ connection, busy, onTest, onDefaults, onChange, onDisconnect }: {
  connection: WordPressConnection; busy: Busy;
  onTest: () => void; onChange: () => void; onDisconnect: () => void;
  onDefaults: (values: Partial<Pick<WordPressConnection, "default_status" | "default_author_id" | "default_category_id">>) => void;
}) {
  const [status, setStatus] = useState(connection.default_status);
  const [author, setAuthor] = useState(connection.default_author_id?.toString() ?? "");
  const [category, setCategory] = useState(connection.default_category_id?.toString() ?? "");
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const ok = !connection.last_error;

  return (
    <div className="space-y-6">
      <div className={ok ? "rounded-lg border border-emerald-200 bg-emerald-50 p-4" : "rounded-lg border border-amber-200 bg-amber-50 p-4"}>
        <p className="flex items-center gap-2 font-medium">
          {ok ? <CheckCircle2Icon className="size-4 text-emerald-700" /> : <TriangleAlertIcon className="size-4 text-amber-700" />}
          {ok ? "Połączono" : "Problem z połączeniem"}
        </p>
        <dl className="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
          <dt className="text-muted-foreground">Strona</dt>
          <dd className="min-w-0 break-all"><a href={connection.site_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 underline underline-offset-4">{connection.site_url}<ExternalLinkIcon className="size-3.5" /></a></dd>
          <dt className="text-muted-foreground">Konto WordPress</dt>
          <dd>{connection.wp_user_name ?? connection.username} <span className="text-muted-foreground">({connection.username})</span></dd>
          <dt className="text-muted-foreground">Wtyczka SEO</dt><dd>{SEO_LABELS[connection.seo_plugin]}</dd>
          <dt className="text-muted-foreground">Publikowanie</dt><dd>{connection.can_publish ? "dozwolone" : "tylko szkice (brak uprawnienia publish_posts)"}</dd>
          {connection.last_checked_at && <><dt className="text-muted-foreground">Sprawdzono</dt><dd>{formatDate(connection.last_checked_at)}</dd></>}
        </dl>
        {!ok && <p className="mt-3 text-sm text-amber-900">{WORDPRESS_MESSAGES[connection.last_error ?? ""] ?? connection.last_error}</p>}
      </div>

      <form className="grid gap-4 sm:grid-cols-3" onSubmit={(event) => {
        event.preventDefault();
        onDefaults({ default_status: status, default_author_id: author ? Number(author) : null, default_category_id: category ? Number(category) : null });
      }}>
        <div className="grid gap-1.5">
          <Label htmlFor="wp-default-status">Domyślny status</Label>
          <select id="wp-default-status" className="h-9 rounded-md border bg-background px-3 text-sm" value={status}
            onChange={(event) => setStatus(event.target.value as WordPressConnection["default_status"])}>
            {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="wp-default-author">ID autora (opcjonalnie)</Label>
          <Input id="wp-default-author" type="number" min={1} value={author} placeholder="Konto połączenia" onChange={(event) => setAuthor(event.target.value)} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="wp-default-category">ID kategorii (opcjonalnie)</Label>
          <Input id="wp-default-category" type="number" min={1} value={category} placeholder="Według artykułu" onChange={(event) => setCategory(event.target.value)} />
        </div>
        <div className="sm:col-span-3"><Button type="submit" variant="outline" disabled={busy !== null}>{busy === "defaults" && <Loader2Icon className="size-4 animate-spin" />}Zapisz ustawienia publikacji</Button></div>
      </form>

      <div className="flex flex-wrap gap-2 border-t pt-4">
        <Button variant="outline" disabled={busy !== null} onClick={onTest}>{busy === "test" && <Loader2Icon className="size-4 animate-spin" />}Sprawdź połączenie</Button>
        <Button variant="outline" disabled={busy !== null} onClick={onChange}>Zmień stronę lub dane logowania</Button>
        {confirmDisconnect ? (
          <span className="flex flex-wrap items-center gap-2 text-sm">
            Rozłączyć? Publikacja zostanie zablokowana do ponownego połączenia.
            <Button variant="destructive" disabled={busy !== null} onClick={onDisconnect}>Rozłącz</Button>
            <Button variant="ghost" onClick={() => setConfirmDisconnect(false)}>Anuluj</Button>
          </span>
        ) : (
          <Button variant="ghost" className="text-rose-700" disabled={busy !== null} onClick={() => setConfirmDisconnect(true)}>Rozłącz</Button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">Po rozłączeniu odwołaj hasło aplikacji „Content Engine” w WordPressie: Użytkownicy → Profil → Hasła aplikacji.</p>
    </div>
  );
}

function ConnectForm({ current, busy, onAuthorize, onManual, onCancel }: {
  current: WordPressConnection | null; busy: Busy; onCancel?: () => void;
  onAuthorize: (siteUrl: string, apiUrl: string | null) => void;
  onManual: (body: { site_url: string; api_url: string | null; username: string; app_password: string }) => void;
}) {
  const [siteUrl, setSiteUrl] = useState(current?.site_url ?? "");
  const [apiUrl, setApiUrl] = useState(current?.api_url ?? "");
  const [manual, setManual] = useState(false);
  const [username, setUsername] = useState(current?.username ?? "");
  const [password, setPassword] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const api_url = apiUrl.trim() || null;
    if (manual) onManual({ site_url: siteUrl.trim(), api_url, username: username.trim(), app_password: password });
    else onAuthorize(siteUrl.trim(), api_url);
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid gap-1.5">
        <Label htmlFor="wp-site-url">Adres strony WordPress</Label>
        <Input id="wp-site-url" type="url" required placeholder="https://twoja-strona.pl" value={siteUrl} onChange={(event) => setSiteUrl(event.target.value)} />
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">Zaawansowane: adres wewnętrzny API</summary>
        <div className="mt-2 grid gap-1.5">
          <Label htmlFor="wp-api-url">Adres, pod którym serwer łączy się z WordPressem (np. w sieci Dockera)</Label>
          <Input id="wp-api-url" type="url" placeholder="Puste = adres strony" value={apiUrl} onChange={(event) => setApiUrl(event.target.value)} />
        </div>
      </details>
      {manual ? (
        <div className="grid gap-4 rounded-lg border p-4 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="wp-username">Login WordPress</Label>
            <Input id="wp-username" required autoComplete="off" value={username} onChange={(event) => setUsername(event.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="wp-app-password">Hasło aplikacji</Label>
            <Input id="wp-app-password" type="password" required autoComplete="new-password" placeholder="xxxx xxxx xxxx xxxx xxxx xxxx" value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>
          <p className="text-xs text-muted-foreground sm:col-span-2">Utwórz je w WordPressie: Użytkownicy → Profil → Hasła aplikacji. To nie jest hasło logowania.</p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">Przeniesiemy Cię do WordPressa. Zaloguj się i zatwierdź dostęp dla „Content Engine”; WordPress utworzy hasło aplikacji i odeśle Cię tutaj.</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={busy !== null}>
          {(busy === "authorize" || busy === "manual") && <Loader2Icon className="size-4 animate-spin" />}
          {manual ? "Połącz" : "Połącz z WordPressem"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setManual(!manual)}>{manual ? "Połącz przez WordPress (zalecane)" : "Połącz ręcznie (hasło aplikacji)"}</Button>
        {onCancel && <Button type="button" variant="ghost" onClick={onCancel}>Anuluj</Button>}
      </div>
    </form>
  );
}

function BridgeHelp() {
  return (
    <details className="rounded-lg bg-muted/40 p-4 text-sm">
      <summary className="cursor-pointer font-medium">Wymagania po stronie WordPressa</summary>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
        <li>Wtyczka <strong>Content Engine Bridge</strong> zainstalowana i aktywna (chroni przed duplikatami i nadpisaniem ręcznych zmian).</li>
        <li>WordPress 5.6+ z włączonymi hasłami aplikacji; strona po HTTPS (wymóg WordPressa dla autoryzacji aplikacji).</li>
        <li>Konto z uprawnieniem do edycji wpisów; publikowanie wymaga roli z uprawnieniem publikacji.</li>
        <li>Opcjonalnie Yoast SEO albo Rank Math – wykrywane automatycznie.</li>
      </ul>
    </details>
  );
}
