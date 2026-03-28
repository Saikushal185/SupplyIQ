import { Card, Metric, Text } from "@tremor/react";
import clsx from "clsx";

import { StatusBadge } from "@/components/ui/StatusBadge";

interface StatCardProps {
  label: string;
  value: string;
  note: string;
  accent?: "indigo" | "cyan" | "amber" | "rose" | "emerald";
}

export function StatCard({ label, value, note, accent = "indigo" }: StatCardProps) {
  return (
    <Card className="rounded-[28px] border border-white/10 bg-app-surface/90 p-5 shadow-panel ring-0">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Text className="text-slate-400">{label}</Text>
          <Metric className={clsx("mono-data mt-4 text-white")}>{value}</Metric>
        </div>
        <StatusBadge label={accent} variant={accent} />
      </div>
      <p className="mt-4 text-sm text-slate-400">{note}</p>
    </Card>
  );
}
