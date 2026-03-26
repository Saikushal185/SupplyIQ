"use client";

import { SectionCard } from "@/components/ui/SectionCard";
import { usePipelineStatus } from "@/lib/hooks";

function LoadingState() {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-6 text-sm text-slate-300">
      Loading pipeline status...
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 p-6 text-sm text-rose-100">{message}</div>
  );
}

export function PipelinePageClient() {
  const pipelineStatus = usePipelineStatus();

  if (pipelineStatus.error) {
    return <ErrorState message="Unable to load pipeline status. Confirm Prefect Cloud access and your session token." />;
  }

  if (!pipelineStatus.data) {
    return <LoadingState />;
  }

  const status = pipelineStatus.data.data;

  return (
    <div className="space-y-6">
      <SectionCard
        title="Pipeline Status"
        subtitle="Latest Prefect Cloud flow run visibility for operational administrators."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">Flow Run</p>
            <p className="mt-2 text-sm font-semibold text-white">{status.flow_run_id ?? "Unavailable"}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">Run Name</p>
            <p className="mt-2 text-sm font-semibold text-white">{status.flow_name ?? "Unavailable"}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">State</p>
            <p className="mt-2 text-sm font-semibold text-white">{status.state_name ?? status.state_type ?? "Unknown"}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">Started</p>
            <p className="mt-2 text-sm font-semibold text-white">
              {status.start_time ? new Date(status.start_time).toLocaleString() : "Unavailable"}
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-300">
          <p>Deployment ID: {status.deployment_id ?? "Unavailable"}</p>
          <p className="mt-2">Finished: {status.end_time ? new Date(status.end_time).toLocaleString() : "Not finished"}</p>
        </div>
      </SectionCard>
    </div>
  );
}
