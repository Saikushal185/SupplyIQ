import type {
  ForecastFeatureContribution,
  ForecastRecordResponse,
  InventoryTurnoverTrendBucket,
  InventoryTurnoverTrendPeriod,
  PipelineStatus,
  ProductSalesSummaryItem,
  SalesAnalyticsItem,
  SeverityLevel,
  SupplierPerformanceItem,
} from "@/types";

export const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const monthFormatter = new Intl.DateTimeFormat(undefined, { month: "short", year: "2-digit" });
const monthLabelFormatter = new Intl.DateTimeFormat(undefined, { month: "short" });
const shortDateFormatter = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function padDatePart(value: number) {
  return String(value).padStart(2, "0");
}

function parseIsoDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function parseYearMonth(value: string) {
  const [year, month] = value.split("-").map(Number);
  return new Date(year, month - 1, 1);
}

export function toIsoDate(date: Date) {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`;
}

export function getTodayIsoDate() {
  return toIsoDate(new Date());
}

export function getMonthStartIsoDate(reference = new Date()) {
  return toIsoDate(new Date(reference.getFullYear(), reference.getMonth(), 1));
}

export function getRelativeDateRange(days: number, endDate = new Date()) {
  const resolvedEnd = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate());
  const resolvedStart = new Date(resolvedEnd);
  resolvedStart.setDate(resolvedStart.getDate() - Math.max(days - 1, 0));
  return {
    startDate: toIsoDate(resolvedStart),
    endDate: toIsoDate(resolvedEnd),
  };
}

export function buildMonthlyPeriods(endDateValue: string): InventoryTurnoverTrendPeriod[] {
  const endDate = parseIsoDate(endDateValue);
  return Array.from({ length: 6 }, (_, index) => {
    const offset = 5 - index;
    const start = new Date(endDate.getFullYear(), endDate.getMonth() - offset, 1);
    const naturalEnd = new Date(start.getFullYear(), start.getMonth() + 1, 0);
    const resolvedEnd = offset === 0 && naturalEnd > endDate ? endDate : naturalEnd;
    const isoStart = toIsoDate(start);
    const isoEnd = toIsoDate(resolvedEnd);

    return {
      key: `${isoStart}:${isoEnd}`,
      label: monthLabelFormatter.format(start),
      startDate: isoStart,
      endDate: isoEnd,
    };
  });
}

export function formatShortDate(value: string) {
  return shortDateFormatter.format(parseIsoDate(value));
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "Unavailable";
  }
  return dateTimeFormatter.format(new Date(value));
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number, fractionDigits = 1) {
  return `${value.toFixed(fractionDigits)}%`;
}

export function severityToVariant(severity: SeverityLevel) {
  if (severity === "critical" || severity === "high") {
    return "rose" as const;
  }
  if (severity === "medium") {
    return "amber" as const;
  }
  return "emerald" as const;
}

export function pipelineStatusVariant(status: PipelineStatus | null | undefined) {
  const state = `${status?.state_name ?? status?.state_type ?? ""}`.toLowerCase();
  if (state.includes("complete") || state.includes("success") || state.includes("healthy")) {
    return "emerald" as const;
  }
  if (state.includes("running") || state.includes("queued") || state.includes("pending")) {
    return "cyan" as const;
  }
  return "rose" as const;
}

export function buildSalesTrend(rows: SalesAnalyticsItem[]) {
  const totalsByDate = new Map<string, number>();

  rows.forEach((row) => {
    totalsByDate.set(row.sale_date, (totalsByDate.get(row.sale_date) ?? 0) + row.units_sold);
  });

  const sortedEntries = [...totalsByDate.entries()].sort((left, right) => left[0].localeCompare(right[0]));
  return {
    labels: sortedEntries.map(([saleDate]) => formatShortDate(saleDate)),
    values: sortedEntries.map(([, units]) => units),
  };
}

export function buildTopProducts(rows: ProductSalesSummaryItem[], limit = 5) {
  return rows
    .slice()
    .sort((left, right) => right.units_sold - left.units_sold)
    .slice(0, limit)
    .map((row) => ({
      label: row.product_name,
      value: row.units_sold,
      sku: row.sku,
    }));
}

function toWeekdayIndex(dateValue: string) {
  const day = parseIsoDate(dateValue).getDay();
  return day === 0 ? 6 : day - 1;
}

export function buildHeatmap(rows: SalesAnalyticsItem[], selectedRegionIds: string[]) {
  const filteredRows = selectedRegionIds.length
    ? rows.filter((row) => selectedRegionIds.includes(row.region_id))
    : rows;

  const regionLabels = [...new Set(filteredRows.map((row) => row.region_name))].sort((left, right) => left.localeCompare(right));
  const regionIndexByName = new Map(regionLabels.map((label, index) => [label, index]));
  const totals = new Map<string, number>();

  filteredRows.forEach((row) => {
    const regionIndex = regionIndexByName.get(row.region_name);
    if (regionIndex === undefined) {
      return;
    }
    const weekdayIndex = toWeekdayIndex(row.sale_date);
    const key = `${regionIndex}:${weekdayIndex}`;
    totals.set(key, (totals.get(key) ?? 0) + row.units_sold);
  });

  return {
    regions: regionLabels,
    values: [...totals.entries()].map(([key, total]) => {
      const [regionIndex, weekdayIndex] = key.split(":").map(Number);
      return [weekdayIndex, regionIndex, total] as [number, number, number];
    }),
  };
}

export function buildRevenueGrowthSeries(rows: SalesAnalyticsItem[], selectedRegionIds: string[]) {
  const filteredRows = selectedRegionIds.length
    ? rows.filter((row) => selectedRegionIds.includes(row.region_id))
    : rows;

  const revenueByRegionMonth = new Map<string, number>();
  const regionNames = new Map<string, string>();
  filteredRows.forEach((row) => {
    const monthKey = row.sale_date.slice(0, 7);
    const key = `${row.region_id}:${monthKey}`;
    regionNames.set(row.region_id, row.region_name);
    revenueByRegionMonth.set(key, (revenueByRegionMonth.get(key) ?? 0) + row.revenue);
  });

  const months = [...new Set(filteredRows.map((row) => row.sale_date.slice(0, 7)))].sort((left, right) => left.localeCompare(right));
  const labels = months.map((month) => monthFormatter.format(parseYearMonth(month)));

  const series = [...regionNames.entries()]
    .sort((left, right) => left[1].localeCompare(right[1]))
    .map(([regionId, regionName]) => {
      let previousRevenue = 0;
      const data = months.map((month) => {
        const revenue = revenueByRegionMonth.get(`${regionId}:${month}`) ?? 0;
        const delta = revenue - previousRevenue;
        previousRevenue = revenue;
        return Number(delta.toFixed(2));
      });
      return {
        name: regionName,
        data,
      };
    });

  return {
    labels,
    series,
  };
}

export function buildTurnoverTrendSeries(
  buckets: InventoryTurnoverTrendBucket[],
  categoryProductIds: Set<string> | null,
  limit = 5,
) {
  const seriesMap = new Map<string, { name: string; data: number[] }>();

  buckets.forEach((bucket, bucketIndex) => {
    bucket.rows.forEach((row) => {
      if (categoryProductIds && !categoryProductIds.has(row.product_id)) {
        return;
      }

      const current =
        seriesMap.get(row.product_id) ??
        {
          name: row.product_name,
          data: new Array(buckets.length).fill(0),
        };
      current.data[bucketIndex] = row.turnover_ratio;
      seriesMap.set(row.product_id, current);
    });
  });

  const rankedSeries = [...seriesMap.values()]
    .sort((left, right) => {
      const leftLatest = left.data[left.data.length - 1] ?? 0;
      const rightLatest = right.data[right.data.length - 1] ?? 0;
      return rightLatest - leftLatest;
    })
    .slice(0, limit);

  return {
    labels: buckets.map((bucket) => bucket.label),
    series: rankedSeries,
  };
}

export function buildSupplierReliabilitySeries(items: SupplierPerformanceItem[]) {
  return items.slice().sort((left, right) => left.on_time_rate_pct - right.on_time_rate_pct);
}

export function reliabilityColor(value: number) {
  if (value < 75) {
    return "#ef4444";
  }
  if (value < 90) {
    return "#f59e0b";
  }
  return "#22c55e";
}

function featureDisplayName(feature: string) {
  return feature
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function featureDirection(feature: ForecastFeatureContribution) {
  if (feature.direction) {
    return feature.direction;
  }
  return feature.contribution >= 0 ? "up" : "down";
}

export function buildForecastInsight(forecast: ForecastRecordResponse | null) {
  const features = forecast?.shap_json.top_features ?? [];
  const weatherFeature = features.find((feature) => feature.feature === "weather_temp");
  const primaryFeature = weatherFeature ?? features[0];

  if (!primaryFeature) {
    return "Model explainability will appear after a forecast run completes.";
  }

  const direction = featureDirection(primaryFeature) === "up" ? "+" : "-";
  const scaledMagnitude =
    Math.abs(primaryFeature.contribution) > 1
      ? Math.abs(primaryFeature.contribution)
      : Math.abs(primaryFeature.contribution) * 100;
  const magnitude = Math.max(1, Math.round(scaledMagnitude));

  if (primaryFeature.feature === "weather_temp") {
    return `Weather is driving a ${direction}${magnitude}% demand spike in this region`;
  }

  return `${featureDisplayName(primaryFeature.feature)} is driving a ${direction}${magnitude}% demand shift in this region`;
}

export function findStockoutDate(currentQuantity: number, forecast: ForecastRecordResponse | null) {
  if (!forecast) {
    return null;
  }

  let remainingQuantity = currentQuantity;
  for (const point of forecast.forecast_json.predictions) {
    remainingQuantity -= point.predicted_units ?? point.units ?? 0;
    if (remainingQuantity <= 0) {
      return point.date;
    }
  }

  return null;
}

export function buildForecastBand(forecast: ForecastRecordResponse | null) {
  const points = forecast?.forecast_json.predictions ?? [];
  return {
    labels: points.map((point) => formatShortDate(point.date)),
    predicted: points.map((point) => point.predicted_units ?? point.units),
    lower: points.map((point) => point.lower_bound ?? point.lower),
    upper: points.map((point) => point.upper_bound ?? point.upper),
  };
}

export function buildShapSeries(forecast: ForecastRecordResponse | null) {
  return (forecast?.shap_json.top_features ?? []).slice(0, 5).map((feature) => ({
    label: feature.feature,
    displayLabel: featureDisplayName(feature.feature),
    value: Number((Math.abs(feature.contribution) > 1 ? feature.contribution : feature.contribution * 100).toFixed(2)),
    direction: featureDirection(feature),
  }));
}
