import { AutomationCard } from "@/components/settings/automation-card";
import { CostReportCard } from "@/components/settings/cost-report";
import { EditorialCard } from "@/components/settings/editorial-card";
import { UsageCard } from "@/components/settings/usage-card";
import { WordPressConnectionCard } from "@/components/settings/wordpress-connection";

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Ustawienia</h1>
        <p className="text-sm text-muted-foreground">Automatyka i integracje tego workspace&apos;u.</p>
      </div>
      <UsageCard />
      <CostReportCard />
      <AutomationCard />
      <EditorialCard />
      <WordPressConnectionCard />
    </div>
  );
}
