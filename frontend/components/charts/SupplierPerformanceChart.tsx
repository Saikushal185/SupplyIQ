"use client";

import dynamic from "next/dynamic";

import type { SupplierPerformanceItem } from "@/types";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface SupplierPerformanceChartProps {
  items: SupplierPerformanceItem[];
}

export function SupplierPerformanceChart({ items }: SupplierPerformanceChartProps) {
  const option = {
    tooltip: { trigger: "axis" },
    grid: { left: 20, right: 20, top: 20, bottom: 20, containLabel: true },
    xAxis: {
      type: "value",
      max: 100,
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.12)" } },
    },
    yAxis: {
      type: "category",
      data: items.map((item) => item.supplier_name),
      axisLabel: { color: "#cbd5e1" },
    },
    series: [
      {
        type: "bar",
        data: items.map((item) => item.on_time_rate_pct),
        itemStyle: { color: "#f4a261", borderRadius: [6, 6, 6, 6] },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 340 }} />;
}
