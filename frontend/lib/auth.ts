import "server-only";

import { auth, currentUser } from "@clerk/nextjs/server";

import { guestSessionSnapshot, isClerkConfigured, signedOutSessionSnapshot } from "@/lib/auth-config";
import { enrichSessionSnapshot, normalizeUserRole } from "@/lib/roles";
import type { SessionSnapshot } from "@/types";

function readClerkRole(value: unknown) {
  if (value && typeof value === "object" && "role" in value) {
    return normalizeUserRole((value as Record<string, unknown>).role);
  }
  return "viewer";
}

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
    return signedOutSessionSnapshot;
  }

  const user = await currentUser();
  return enrichSessionSnapshot({
    isLoaded: true,
    isSignedIn: true,
    userId: authState.userId,
    displayName: user?.fullName ?? user?.username ?? "Supply Chain Manager",
    primaryEmail: user?.primaryEmailAddress?.emailAddress ?? null,
    role: readClerkRole(user?.publicMetadata),
    roleLabel: "Authenticated",
    canViewForecast: false,
    canGenerateForecast: false,
    canViewPipeline: false,
    getToken: async () => authState.getToken(),
  });
}
