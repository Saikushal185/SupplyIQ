import assert from "node:assert/strict";

async function run(name: string, assertion: () => Promise<void> | void) {
  try {
    await assertion();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}

await run("dashboard readiness allows the page to render when pipeline status failed", async () => {
  const mod = await import("./view-state.ts").catch(() => null);
  assert.ok(mod?.isDashboardReady);

  assert.equal(
    mod.isDashboardReady({
      hasInventorySummary: true,
      hasLowStock: true,
      hasSales: true,
      hasProductSales: true,
      hasForecastRunCount: true,
      canViewPipeline: true,
      hasPipelineStatus: false,
      hasPipelineStatusError: true,
    }),
    true,
  );
});

await run("forecast result state treats a missing latest forecast as empty", async () => {
  const mod = await import("./view-state.ts").catch(() => null);
  assert.ok(mod?.getForecastResultState);

  assert.equal(
    mod.getForecastResultState({
      hasSelectedPosition: true,
      isLoading: false,
      hasError: false,
      hasData: false,
    }),
    "empty",
  );
});
