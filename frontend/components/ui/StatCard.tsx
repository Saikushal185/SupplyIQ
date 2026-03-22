import { Badge, Card, Metric, Text } from "@tremor/react";

interface StatCardProps {
  label: string;
  value: string;
  note: string;
  accent?: string;
}

export function StatCard({ label, value, note, accent = "teal" }: StatCardProps) {
  return (
    <Card className="border border-white/10 bg-slate-900/80 shadow-glow">
      <Text className="text-slate-400">{label}</Text>
      <Metric className="mt-3 text-white">{value}</Metric>
      <div className="mt-4 flex items-center justify-between">
        <Text className="max-w-[18rem] text-slate-400">{note}</Text>
        <Badge color={accent as "teal" | "orange" | "rose"}>{accent}</Badge>
      </div>
    </Card>
  );
}
