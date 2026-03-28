import clsx from "clsx";
import type { PropsWithChildren, ReactNode } from "react";

interface SectionCardProps extends PropsWithChildren {
  title: string;
  subtitle: string;
  action?: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function SectionCard({ title, subtitle, action, className, bodyClassName, children }: SectionCardProps) {
  return (
    <section className={clsx("panel-surface p-5 md:p-6", className)}>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="eyebrow">SupplyIQ Insight</p>
          <h3 className="panel-title">{title}</h3>
          <p className="max-w-3xl text-sm text-slate-400">{subtitle}</p>
        </div>
        {action}
      </div>
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}
