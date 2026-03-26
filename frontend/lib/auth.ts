import "server-only";

import { redirect } from "next/navigation";
import { auth } from "@clerk/nextjs/server";

import { guestSessionSnapshot } from "@/lib/auth-config";
import { enrichSessionSnapshot, getDefaultRouteForRole, normalizeUserRole } from "@/lib/roles";
import type { SessionSnapshot, UserRole } from "@/types";

function getStringClaim(claims: Record<string, unknown> | null, key: string): string | null {
  const value = claims?.[key];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function getDisplayNameFromClaims(claims: Record<string, unknown> | null): string {
  const fullName = getStringClaim(claims, "full_name");
  if (fullName) {
    return fullName;
  }

  const joinedName = [getStringClaim(claims, "first_name"), getStringClaim(claims, "last_name")]
    .filter(Boolean)
    .join(" ")
    .trim();
  if (joinedName) {
    return joinedName;
  }

  return getStringClaim(claims, "username") ?? "Authenticated User";
}

function getPrimaryEmailFromClaims(claims: Record<string, unknown> | null): string | null {
  return getStringClaim(claims, "email") ?? getStringClaim(claims, "primary_email_address");
}

function getRoleFromClaims(claims: Record<string, unknown> | null): UserRole {
  const publicMetadata = claims?.["public_metadata"];
  if (publicMetadata && typeof publicMetadata === "object" && "role" in publicMetadata) {
    return normalizeUserRole((publicMetadata as Record<string, unknown>).role);
  }

  const publicMetadataCamel = claims?.["publicMetadata"];
  if (publicMetadataCamel && typeof publicMetadataCamel === "object" && "role" in publicMetadataCamel) {
    return normalizeUserRole((publicMetadataCamel as Record<string, unknown>).role);
  }

  return "viewer";
}

/** Returns a server-side bearer token when Clerk auth is enabled. */
export async function getServerSessionToken(): Promise<string | null> {
  const authState = await auth();
  if (!authState.userId) {
    return null;
  }

  return authState.getToken();
}

/** Returns the current server-side session summary for SSR boundaries. */
export async function getServerSessionSnapshot(): Promise<SessionSnapshot> {
  const authState = await auth();
  if (!authState.userId) {
    return guestSessionSnapshot;
  }

  const claims = (authState.sessionClaims ?? null) as Record<string, unknown> | null;
  return enrichSessionSnapshot({
    isLoaded: true,
    isSignedIn: true,
    userId: authState.userId,
    displayName: getDisplayNameFromClaims(claims),
    primaryEmail: getPrimaryEmailFromClaims(claims),
    role: getRoleFromClaims(claims),
    roleLabel: "Authenticated",
    canViewForecast: false,
    canGenerateForecast: false,
    canViewPipeline: false,
    getToken: async () => authState.getToken(),
  });
}

/** Redirects unauthenticated or unauthorized users away from protected pages. */
export async function requireServerRole(roles?: UserRole[]): Promise<SessionSnapshot> {
  const session = await getServerSessionSnapshot();

  if (!session.isSignedIn) {
    redirect("/login");
  }

  if (roles && !roles.includes(session.role)) {
    redirect(getDefaultRouteForRole(session.role));
  }

  return session;
}
