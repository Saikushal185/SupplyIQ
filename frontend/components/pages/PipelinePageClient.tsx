"use client";

import { AlertTriangle, CalendarClock, DatabaseZap, Workflow } from "lucide-react";

import { SectionCard } from "@/components/ui/SectionCard";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDateTime, pipelineStatusVariant } from "@/lib/insights";
import { usePipelineStatus } from "@/lib/hooks";

function LoadingState() {
  return (
    <div className="panel-surface p-6">
      <SkeletonBlock className="h-4 w-40" />
      <SkeletonBlock className="mt-3 h-4 w-80" />
      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock key={index} className="h-24 w-full rounded-[24px]" />
        ))}
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="panel-surface flex items-start gap-4 p-6 text-rose-100">
      <AlertTriangle className="mt-1 h-5 w-5 shrink-0" />
      <div>
        <p className="text-lg font-semibold text-white">Pipeline data is unavailable</p>
        <p className="mt-2 text-sm text-rose-100/90">{message}</p>
      </div>
    </div>
  );
}

export function PipelinePageClient() {
  const pipelineStatus = usePipelineStatus();
  const pipelineStatusData = pipelineStatus.data;

  if (pipelineStatus.error) {
    return <ErrorState message="Confirm Prefect Cloud access and your session token." />;
  }

  if (!pipelineStatusData) {
    return <LoadingState />;
  }

  const status = pipelineStatusData.data;

  return (
    <SectionCard
      title="Pipeline Status"
      subtitle="Latest operational telemetry for the orchestration pipeline and its next scheduled refresh."
      action={<StatusBadge label={status.state_name ?? "Unknown"} variant={pipelineStatusVariant(status)} />}
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Workflow className="h-4 w-4" />
            Flow run
          </div>
          <p className="mono-data mt-3 text-sm text-white">{status.flow_run_id ?? "Unavailable"}</p>
        </div>
        <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
          <p className="text-sm text-slate-400">Run name</p>
          <p className="mt-3 text-sm font-semibold text-white">{status.flow_name ?? "Unavailable"}</p>
        </div>
        <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <CalendarClock className="h-4 w-4" />
            Started
          </div>
          <p className="mono-data mt-3 text-sm text-white">{formatDateTime(status.start_time)}</p>
        </div>
        <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <DatabaseZap className="h-4 w-4" />
            Next scheduled run
          </div>
          <p className="mono-data mt-3 text-sm text-white">{formatDateTime(status.next_scheduled_run_time)}</p>
        </div>
      </div>

      <div className="mt-4 rounded-[24px] border border-white/10 bg-slate-950/45 p-4 text-sm text-slate-300">
        <p>Deployment ID: <span className="mono-data text-slate-100">{status.deployment_id ?? "Unavailable"}</span></p>
        <p className="mt-2">Finished: <span className="mono-data text-slate-100">{formatDateTime(status.end_time)}</span></p>
      </div>
    </SectionCard>
  );
}
