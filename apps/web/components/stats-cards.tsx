import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardStats } from "@/types/api";

const ITEMS: { key: keyof DashboardStats; label: string; hint: string }[] = [
  { key: "candidates_today", label: "Candidates today", hint: "Fetched since midnight (UTC)" },
  { key: "new_today", label: "New today", hint: "Fetched today, still pending" },
  { key: "approved", label: "Approved", hint: "All time" },
  { key: "ignored", label: "Ignored", hint: "All time" },
  { key: "average_score", label: "Average score", hint: "Across classified candidates" },
];

export function StatsCards({ stats }: { stats: DashboardStats | null }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      {ITEMS.map((item) => (
        <Card key={item.key}>
          <CardHeader>
            <CardDescription>{item.label}</CardDescription>
            <CardTitle className="text-3xl font-semibold tabular-nums">
              {stats === null ? "…" : (stats[item.key] ?? "—")}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">{item.hint}</CardContent>
        </Card>
      ))}
    </div>
  );
}
