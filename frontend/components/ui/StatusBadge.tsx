import clsx from "clsx";

const variantClasses = {
  slate: "border-white/10 bg-white/5 text-slate-200",
  indigo: "border-indigo-400/20 bg-indigo-400/10 text-indigo-100",
  cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-100",
  emerald: "border-emerald-400/20 bg-emerald-400/10 text-emerald-100",
  amber: "border-amber-400/20 bg-amber-400/10 text-amber-100",
  rose: "border-rose-400/20 bg-rose-400/10 text-rose-100",
} as const;

interface StatusBadgeProps {
  label: string;
  variant?: keyof typeof variantClasses;
  className?: string;
}

export function StatusBadge({ label, variant = "slate", className }: StatusBadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.28em]",
        variantClasses[variant],
        className,
      )}
    >
      {label}
    </span>
  );
}
