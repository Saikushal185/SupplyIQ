import assert from "node:assert/strict";

import * as insights from "./insights.ts";
import {
  buildHeatmap,
  buildRevenueGrowthSeries,
  formatShortDate,
  getRelativeDateRange,
  getTodayIsoDate,
  toIsoDate,
} from "./insights.ts";

function run(name: string, assertion: () => void) {
  try {
    assertion();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}

run("toIsoDate preserves the local calendar date", () => {
  assert.equal(toIsoDate(new Date(2026, 2, 1)), "2026-03-01");
});

run("getTodayIsoDate uses the local calendar day", () => {
  const now = new Date();
  const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  assert.equal(getTodayIsoDate(), expected);
});

run("getRelativeDateRange keeps local day boundaries", () => {
  assert.deepEqual(getRelativeDateRange(3, new Date(2026, 2, 28)), {
    startDate: "2026-03-26",
    endDate: "2026-03-28",
  });
});

run("buildMonthlyPeriods keeps the selected month boundaries intact", () => {
  assert.ok(insights.buildMonthlyPeriods);
  assert.deepEqual(insights.buildMonthlyPeriods("2026-03-28").at(-1), {
    key: "2026-03-01:2026-03-28",
    label: "Mar",
    startDate: "2026-03-01",
    endDate: "2026-03-28",
  });
});

run("formatShortDate does not shift a plain ISO date into the prior day", () => {
  const expected = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(2026, 2, 1));
  assert.equal(formatShortDate("2026-03-01"), expected);
});

run("buildHeatmap buckets a Sunday sale as Sunday", () => {
  const heatmap = buildHeatmap(
    [
      {
        sale_date: "2026-03-01",
        region_id: "region-1",
        region_name: "West",
        units_sold: 12,
        revenue: 2400,
      },
    ],
    [],
  );

  assert.deepEqual(heatmap.values, [[6, 0, 12]]);
});

run("buildRevenueGrowthSeries keeps first-of-month sales in their month", () => {
  const series = buildRevenueGrowthSeries(
    [
      {
        sale_date: "2026-03-01",
        region_id: "region-1",
        region_name: "West",
        units_sold: 10,
        revenue: 100,
      },
      {
        sale_date: "2026-04-01",
        region_id: "region-1",
        region_name: "West",
        units_sold: 12,
        revenue: 160,
      },
    ],
    [],
  );

  assert.deepEqual(series.series, [
    {
      name: "West",
      data: [100, 60],
    },
  ]);
});
