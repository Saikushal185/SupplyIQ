"use client";

import type { PropsWithChildren } from "react";
import { SWRConfig } from "swr";

const swrConfig = {
  revalidateOnFocus: false,
  revalidateIfStale: true,
  shouldRetryOnError: false,
};

/** Wraps the app with the SWR caching provider. */
export function AppProviders({ children }: PropsWithChildren) {
  return <SWRConfig value={swrConfig}>{children}</SWRConfig>;
}
