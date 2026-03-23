"use client";

import type { PropsWithChildren } from "react";
import { ClerkProvider } from "@clerk/nextjs";
import { SWRConfig } from "swr";

import { SessionProvider } from "@/context/session-context";
import { isClerkConfigured } from "@/lib/auth-config";

const swrConfig = {
  revalidateOnFocus: false,
  revalidateIfStale: true,
  shouldRetryOnError: false,
};

/** Wraps the app with Clerk, session state, and SWR caching providers. */
export function AppProviders({ children }: PropsWithChildren) {
  const clerkEnabled = isClerkConfigured();

  if (!clerkEnabled) {
    return (
      <SWRConfig value={swrConfig}>
        <SessionProvider clerkEnabled={false}>{children}</SessionProvider>
      </SWRConfig>
    );
  }

  return (
    <ClerkProvider
      signInUrl="/login"
      signInFallbackRedirectUrl="/dashboard"
      signUpFallbackRedirectUrl="/dashboard"
      afterSignOutUrl="/login"
    >
      <SWRConfig value={swrConfig}>
        <SessionProvider clerkEnabled>{children}</SessionProvider>
      </SWRConfig>
    </ClerkProvider>
  );
}
