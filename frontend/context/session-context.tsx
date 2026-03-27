"use client";

import { createContext, useContext, type PropsWithChildren } from "react";
import { ClerkLoaded, useAuth, useUser } from "@clerk/nextjs";

import { guestSessionSnapshot } from "@/lib/auth-config";
import type { SessionSnapshot } from "@/types";

const loadingSessionSnapshot: SessionSnapshot = {
  ...guestSessionSnapshot,
  isLoaded: false,
  roleLabel: "Authenticating",
};

const SessionContext = createContext<SessionSnapshot>(guestSessionSnapshot);

function ClerkSessionBridge({ children }: PropsWithChildren) {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();
  const { user } = useUser();

  const value: SessionSnapshot = {
    isLoaded,
    isSignedIn: Boolean(isSignedIn),
    userId: userId ?? null,
    displayName: user?.fullName ?? user?.username ?? "Supply Chain Manager",
    primaryEmail: user?.primaryEmailAddress?.emailAddress ?? null,
    roleLabel: isSignedIn ? "Authenticated" : "Awaiting Sign-In",
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
