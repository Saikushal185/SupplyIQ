export interface DashboardReadyArgs {
  hasInventorySummary: boolean;
  hasLowStock: boolean;
  hasSales: boolean;
  hasProductSales: boolean;
  hasForecastRunCount: boolean;
  canViewPipeline: boolean;
  hasPipelineStatus: boolean;
  hasPipelineStatusError: boolean;
}

export function isDashboardReady({
  hasInventorySummary,
  hasLowStock,
  hasSales,
  hasProductSales,
  hasForecastRunCount,
  canViewPipeline,
  hasPipelineStatus,
  hasPipelineStatusError,
}: DashboardReadyArgs) {
  const coreDataReady = hasInventorySummary && hasLowStock && hasSales && hasProductSales && hasForecastRunCount;
  const pipelineReady = !canViewPipeline || hasPipelineStatus || hasPipelineStatusError;
  return coreDataReady && pipelineReady;
}

export interface ForecastResultStateArgs {
  hasSelectedPosition: boolean;
  isLoading: boolean;
  hasError: boolean;
  hasData: boolean;
}

export type ForecastResultState = "loading" | "error" | "result" | "empty";

export function getForecastResultState({
  hasSelectedPosition,
  isLoading,
  hasError,
  hasData,
}: ForecastResultStateArgs): ForecastResultState {
  if (!hasSelectedPosition) {
    return "empty";
  }
  if (isLoading) {
    return "loading";
  }
  if (hasError) {
    return "error";
  }
  if (hasData) {
    return "result";
  }
  return "empty";
}
