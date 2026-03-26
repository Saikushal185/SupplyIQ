"use client";

import { createContext, useContext, type PropsWithChildren } from "react";
import { ClerkLoaded, useAuth, useUser } from "@clerk/nextjs";

import { guestSessionSnapshot } from "@/lib/auth-config";
import { enrichSessionSnapshot, normalizeUserRole } from "@/lib/roles";
import type { SessionSnapshot } from "@/types";

const loadingSessionSnapshot: SessionSnapshot = {
  ...guestSessionSnapshot,
  isLoaded: false,
};

const SessionContext = createContext<SessionSnapshot>(guestSessionSnapshot);

function ClerkSessionBridge({ children }: PropsWithChildren) {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();
  const { user } = useUser();
  const role = normalizeUserRole(user?.publicMetadata?.role);

  const value = enrichSessionSnapshot({
    isLoaded,
    isSignedIn: Boolean(isSignedIn),
    userId: userId ?? null,
    displayName: user?.fullName ?? user?.username ?? "Supply Chain Manager",
    primaryEmail: user?.primaryEmailAddress?.emailAddress ?? null,
    role,
    roleLabel: role,
    canViewForecast: false,
    canGenerateForecast: false,
    canViewPipeline: false,
    getToken,
  });

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

/** Provides a consistent session context for Clerk-backed app runs. */
export function SessionProvider({ children }: PropsWithChildren) {
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
