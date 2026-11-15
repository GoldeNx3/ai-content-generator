import { AccountCard, PasswordCard } from "@/components/settings/account-card";
import { AutomationCard } from "@/components/settings/automation-card";
import { CostReportCard } from "@/components/settings/cost-report";
import { DemoCard } from "@/components/settings/demo-card";
import { EditorialCard } from "@/components/settings/editorial-card";
import { SettingsNav, SettingsSection } from "@/components/settings/settings-layout";
import { UsageCard } from "@/components/settings/usage-card";
import { WordPressConnectionCard } from "@/components/settings/wordpress-connection";
import { PageHeader } from "@/components/ui/page-header";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Konfiguracja"
        title="Ustawienia"
        description="Konto, budżet AI, automatyzacja, profil redakcyjny, integracja z WordPressem i tematy demo – wszystko dla tego workspace'u."
      />
      <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-10">
        <aside className="sticky top-14 z-20 min-w-0 lg:top-24 lg:self-start"><SettingsNav /></aside>
        <div className="settings-cards min-w-0 space-y-12">
          <SettingsSection id="konto">
            <AccountCard />
            <PasswordCard />
          </SettingsSection>
          <SettingsSection id="koszty">
            <UsageCard />
            <CostReportCard />
          </SettingsSection>
          <SettingsSection id="automatyzacja">
            <AutomationCard />
          </SettingsSection>
          <SettingsSection id="redakcja">
            <EditorialCard />
          </SettingsSection>
          <SettingsSection id="integracje">
            <WordPressConnectionCard />
          </SettingsSection>
          <SettingsSection id="demo">
            <DemoCard />
          </SettingsSection>
        </div>
      </div>
    </div>
  );
}
