"use client";

import { useMemo } from "react";

import { ForecastWorkspace } from "@/components/ui/ForecastWorkspace";
import { SkeletonBlock } from "@/components/ui/Skeleton";
import { useInventorySummary } from "@/lib/hooks";

function ForecastSkeleton() {
  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <div className="panel-surface p-6">
        <SkeletonBlock className="h-4 w-28" />
        <SkeletonBlock className="mt-3 h-10 w-full rounded-2xl" />
        <SkeletonBlock className="mt-4 h-32 w-full rounded-[24px]" />
        <SkeletonBlock className="mt-5 h-12 w-full rounded-2xl" />
      </div>
      <div className="space-y-6">
        <div className="panel-surface p-6">
          <SkeletonBlock className="h-4 w-36" />
          <SkeletonBlock className="mt-3 h-[320px] w-full rounded-[24px]" />
        </div>
        <div className="panel-surface p-6">
          <SkeletonBlock className="h-4 w-32" />
          <SkeletonBlock className="mt-3 h-[280px] w-full rounded-[24px]" />
        </div>
      </div>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="panel-surface p-6 text-rose-100">
      <p className="text-lg font-semibold text-white">Forecast workspace is unavailable</p>
      <p className="mt-2 text-sm text-rose-100/90">{message}</p>
    </div>
  );
}

export function ForecastPageClient() {
  const positions = useInventorySummary();
  const sortedPositions = useMemo(
    () => positions.data?.data.slice().sort((left, right) => left.product_name.localeCompare(right.product_name)) ?? [],
    [positions.data],
  );

  if (positions.error) {
    return <ErrorState message="Check backend connectivity or your session token and try again." />;
  }

  if (!positions.data) {
    return <ForecastSkeleton />;
  }

  return <ForecastWorkspace positions={sortedPositions} />;
}
