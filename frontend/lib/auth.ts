import "server-only";

import { auth, currentUser } from "@clerk/nextjs/server";

import { guestSessionSnapshot, isClerkConfigured } from "@/lib/auth-config";
import type { SessionSnapshot } from "@/types";

/** Returns a server-side bearer token when Clerk auth is enabled. */
export async function getServerSessionToken(): Promise<string | null> {
  if (!isClerkConfigured()) {
    return null;
  }

  const authState = await auth();
  if (!authState.userId) {
    return null;
  }

  return authState.getToken();
}

/** Returns the current server-side session summary for SSR boundaries. */
export async function getServerSessionSnapshot(): Promise<SessionSnapshot> {
  if (!isClerkConfigured()) {
    return guestSessionSnapshot;
  }

  const authState = await auth();
  if (!authState.userId) {
    return guestSessionSnapshot;
  }

  const user = await currentUser();
  return {
    isLoaded: true,
    isSignedIn: true,
    userId: authState.userId,
    displayName: user?.fullName ?? user?.username ?? "Supply Chain Manager",
    primaryEmail: user?.primaryEmailAddress?.emailAddress ?? null,
    roleLabel: "Authenticated",
    getToken: async () => authState.getToken(),
  };
}
