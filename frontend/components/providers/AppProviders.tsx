"use client";

import type { PropsWithChildren } from "react";
import { SWRConfig } from "swr";

import { SessionProvider } from "@/context/session-context";

const swrConfig = {
  revalidateOnFocus: false,
  revalidateIfStale: true,
  shouldRetryOnError: false,
};

/** Wraps the app with Clerk, session state, and SWR caching providers. */
export function AppProviders({ children }: PropsWithChildren) {
  return (
    <SWRConfig value={swrConfig}>
      <SessionProvider>{children}</SessionProvider>
    </SWRConfig>
  );
}
