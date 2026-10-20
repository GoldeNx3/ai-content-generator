"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Loader2Icon } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { ApiError, api, errorText } from "@/lib/api";

// Powrót z ekranu „Autoryzuj aplikację” WordPressa: WP dopisuje user_login i password (hasło aplikacji)
// do adresu. Od razu usuwamy je z paska adresu i historii, a dane przekazujemy do API.
type Credentials = { state: string; user_login: string; password: string };

function readParams(params: URLSearchParams): { credentials: Credentials | null; problem: string | null } {
  const state = params.get("state") ?? "";
  const userLogin = params.get("user_login") ?? "";
  const password = params.get("password") ?? "";
  if (params.get("rejected") === "1" || params.get("success") === "false") {
    return { credentials: null, problem: "Odrzucono dostęp w WordPressie. Połączenie nie zostało utworzone." };
  }
  if (!state || !userLogin || !password) {
    return { credentials: null, problem: "Brak danych autoryzacji z WordPressa. Spróbuj połączyć ponownie." };
  }
  return { credentials: { state, user_login: userLogin, password }, problem: null };
}

export function WordPressCallback() {
  const params = useSearchParams();
  // Odczyt raz, przy pierwszym renderze: zaraz potem adres jest czyszczony z hasła.
  const [{ credentials, problem }] = useState(() => readParams(params));
  const started = useRef(false);
  const [message, setMessage] = useState<string | null>(problem);
  const [needsConfirm, setNeedsConfirm] = useState(false);

  useEffect(() => {
    window.history.replaceState(null, "", "/settings/wordpress/callback");
    if (started.current || !credentials) return;
    started.current = true;
    void complete(credentials, false);
  }, [credentials]);

  async function complete(body: Credentials, confirm: boolean) {
    try {
      await api.completeWordPress({ ...body, confirm_site_change: confirm });
      window.location.replace("/settings?wordpress=connected");
    } catch (err) {
      setNeedsConfirm(err instanceof ApiError && err.detail?.code === "wordpress_site_change_requires_confirmation");
      setMessage(errorText(err));
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4 pt-8">
      <h1 className="text-xl font-semibold">Łączenie z WordPressem</h1>
      {!message && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2Icon className="size-4 animate-spin" />Sprawdzamy połączenie i wtyczkę Content Engine Bridge…</p>}
      {message && <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{message}</p>}
      <div className="flex flex-wrap gap-2">
        {needsConfirm && credentials && <Button onClick={() => { setMessage(null); void complete(credentials, true); }}>Zmień stronę i odepnij stare wpisy</Button>}
        {message && <Link href="/settings" className={buttonVariants({ variant: "outline" })}>Wróć do ustawień</Link>}
      </div>
    </div>
  );
}
