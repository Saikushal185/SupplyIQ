"use client";

import dynamic from "next/dynamic";

import type { DemandPoint } from "@/types";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface DemandAreaChartProps {
  points: DemandPoint[];
}

export function DemandAreaChart({ points }: DemandAreaChartProps) {
  const option = {
    tooltip: { trigger: "axis" },
    grid: { left: 20, right: 20, top: 20, bottom: 20, containLabel: true },
    xAxis: {
      type: "category",
      data: points.map((point) => point.label),
      axisLine: { lineStyle: { color: "#334155" } },
      axisLabel: { color: "#94a3b8" },
    },
    yAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "#334155" } },
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.12)" } },
      axisLabel: { color: "#94a3b8" },
    },
    series: [
      {
        type: "line",
        smooth: true,
        data: points.map((point) => point.demand_units),
        areaStyle: { color: "rgba(25, 167, 176, 0.22)" },
        lineStyle: { color: "#19a7b0", width: 3 },
        itemStyle: { color: "#19a7b0" },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 320 }} />;
}
