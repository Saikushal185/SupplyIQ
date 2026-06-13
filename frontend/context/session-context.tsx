"use client";

import type { SessionSnapshot } from "@/types";

const demoSessionSnapshot: SessionSnapshot = {
  displayName: "Demo Operator",
  primaryEmail: "demo@supplyiq.local",
  roleLabel: "Demo Mode",
};

/** Returns the demo session snapshot shown in the app shell. */
export function useSessionContext(): SessionSnapshot {
  return demoSessionSnapshot;
}
