"use client";

import { createContext, useContext, type PropsWithChildren } from "react";
import { ClerkLoaded, useAuth, useUser } from "@clerk/nextjs";

import { guestSessionSnapshot, signedOutSessionSnapshot } from "@/lib/auth-config";
import { enrichSessionSnapshot, normalizeUserRole } from "@/lib/roles";
import type { SessionSnapshot } from "@/types";

const loadingSessionSnapshot: SessionSnapshot = {
  ...signedOutSessionSnapshot,
  isLoaded: false,
  roleLabel: "Authenticating",
};

const SessionContext = createContext<SessionSnapshot>(guestSessionSnapshot);

function readClerkRole(value: unknown) {
  if (value && typeof value === "object" && "role" in value) {
    return normalizeUserRole((value as Record<string, unknown>).role);
  }
  return "viewer";
}

function ClerkSessionBridge({ children }: PropsWithChildren) {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();
  const { user } = useUser();

  const value: SessionSnapshot = isSignedIn
    ? enrichSessionSnapshot({
        isLoaded,
        isSignedIn: true,
        userId: userId ?? null,
        displayName: user?.fullName ?? user?.username ?? "Supply Chain Manager",
        primaryEmail: user?.primaryEmailAddress?.emailAddress ?? null,
        role: readClerkRole(user?.publicMetadata),
        roleLabel: "Authenticated",
        canViewForecast: false,
        canGenerateForecast: false,
        canViewPipeline: false,
        getToken,
      })
    : {
        ...signedOutSessionSnapshot,
        isLoaded,
        getToken,
      };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

/** Provides a consistent session context for Clerk-backed and demo-mode runs. */
export function SessionProvider({
  children,
  clerkEnabled,
}: PropsWithChildren<{ clerkEnabled: boolean }>) {
  if (!clerkEnabled) {
    return <SessionContext.Provider value={guestSessionSnapshot}>{children}</SessionContext.Provider>;
  }

  return (
    <SessionContext.Provider value={loadingSessionSnapshot}>
      <ClerkLoaded>
        <ClerkSessionBridge>{children}</ClerkSessionBridge>
      </ClerkLoaded>
    </SessionContext.Provider>
  );
}

/** Returns the current authenticated or demo session snapshot. */
export function useSessionContext(): SessionSnapshot {
  return useContext(SessionContext);
}
