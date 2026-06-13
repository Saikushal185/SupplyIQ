import { StatusBadge } from "@/components/ui/StatusBadge";

interface StatCardProps {
  label: string;
  value: string;
  note: string;
  accent?: "indigo" | "cyan" | "amber" | "rose" | "emerald";
}

export function StatCard({ label, value, note, accent = "indigo" }: StatCardProps) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-app-surface/90 p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mono-data mt-4 text-3xl font-semibold text-white">{value}</p>
        </div>
        <StatusBadge label={accent} variant={accent} />
      </div>
      <p className="mt-4 text-sm text-slate-400">{note}</p>
    </div>
  );
}
