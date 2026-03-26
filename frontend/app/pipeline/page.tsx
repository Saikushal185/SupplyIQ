"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useUser } from "@clerk/nextjs";

interface PipelineStatusState {
  status: "success" | "failed";
  lastRun: string;
  nextRun: string;
  refreshedAt: string;
}

function createMockStatus(): PipelineStatusState {
  return {
    status: "success",
    lastRun: "Today 02:00 UTC",
    nextRun: "Tomorrow 02:00 UTC",
    refreshedAt: new Date().toLocaleTimeString(),
  };
}

export default function PipelinePage() {
  const router = useRouter();
  const { user, isLoaded } = useUser();
  const role = typeof user?.publicMetadata?.role === "string" ? user.publicMetadata.role : undefined;
  const [status, setStatus] = useState<PipelineStatusState>(createMockStatus());

  useEffect(() => {
    if (isLoaded && role !== "admin") {
      router.replace("/dashboard");
    }
  }, [isLoaded, role, router]);

  if (!isLoaded) {
    return <div className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 text-slate-300">Loading pipeline access...</div>;
  }

  if (role !== "admin") {
    return <div>Access restricted to administrators.</div>;
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-white/10 bg-slate-950/70 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-white">Pipeline Status</h1>
            <p className="mt-2 text-sm text-slate-400">Mock administrative status card for the Prefect pipeline surface.</p>
          </div>
          <button
            type="button"
            onClick={() => setStatus(createMockStatus())}
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            Refresh
          </button>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">Last pipeline run</p>
            <p className="mt-2 text-lg font-semibold text-white">{status.lastRun}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">Status</p>
            <span
              className={`mt-3 inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${
                status.status === "success"
                  ? "bg-emerald-400/15 text-emerald-100"
                  : "bg-rose-400/15 text-rose-100"
              }`}
            >
              {status.status}
            </span>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-sm text-slate-400">Next scheduled run</p>
            <p className="mt-2 text-lg font-semibold text-white">{status.nextRun}</p>
          </div>
        </div>

        <p className="mt-5 text-sm text-slate-500">Last refreshed at {status.refreshedAt}</p>
      </section>
    </div>
  );
}
