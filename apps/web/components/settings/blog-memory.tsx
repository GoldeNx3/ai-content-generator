"use client";

import { useEffect, useState } from "react";
import { Loader2Icon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { BlogMemory as BlogMemoryState } from "@/types/api";

export function BlogMemory() {
  const [memory, setMemory] = useState<BlogMemoryState | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    api.wordpressPosts().then(setMemory).catch(() => setMemory(null));
  }, []);

  async function sync() {
    setSyncing(true);
    try {
      setMemory(await api.syncWordPressPosts());
      toast.success("Lista wpisów odświeżona.");
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border p-4 text-sm">
      <p>
        {memory?.synced_at
          ? `Pamięć wpisów: ${memory.count} wpisów z bloga (pobrano ${formatDate(memory.synced_at)}).`
          : "Pamięć wpisów: jeszcze nie pobrano listy wpisów."}
      </p>
      <p className="text-xs text-muted-foreground">
        Opublikowane wpisy służą do linków wewnętrznych w kroku pisania i do ostrzeżeń o podobnych tematach. Lista odświeża się sama przed pisaniem (co najwyżej raz na godzinę).
      </p>
      <Button variant="outline" size="sm" disabled={syncing} onClick={sync}>
        {syncing && <Loader2Icon className="size-4 animate-spin" />}Odśwież listę wpisów · bezpłatne
      </Button>
    </div>
  );
}
