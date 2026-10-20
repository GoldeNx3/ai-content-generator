import { WordPressConnectionCard } from "@/components/settings/wordpress-connection";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ustawienia</h1>
        <p className="text-sm text-muted-foreground">Integracje tego workspace&apos;u.</p>
      </div>
      <WordPressConnectionCard />
    </div>
  );
}
