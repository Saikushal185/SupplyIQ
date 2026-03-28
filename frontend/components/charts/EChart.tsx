"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

interface EChartProps {
  option: EChartsOption;
  height?: number;
}

export function EChart({ option, height = 320 }: EChartProps) {
  return <ReactECharts option={option} style={{ height, width: "100%" }} notMerge lazyUpdate />;
}
