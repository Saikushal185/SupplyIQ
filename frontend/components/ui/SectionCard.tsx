import type { PropsWithChildren, ReactNode } from "react";

import { Card, Text, Title } from "@tremor/react";

interface SectionCardProps extends PropsWithChildren {
  title: string;
  subtitle: string;
  action?: ReactNode;
}

export function SectionCard({ title, subtitle, action, children }: SectionCardProps) {
  return (
    <Card className="border border-white/10 bg-slate-900/80 shadow-glow">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <Title className="text-white">{title}</Title>
          <Text className="mt-2 text-slate-400">{subtitle}</Text>
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}
