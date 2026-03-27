import type { SessionSnapshot } from "@/types";

const guestTokenResolver = async (): Promise<string | null> => Promise.resolve(null);

export const guestSessionSnapshot: SessionSnapshot = {
  isLoaded: true,
  isSignedIn: false,
  userId: null,
  displayName: "Guest Operator",
  primaryEmail: null,
  role: "admin",
  roleLabel: "Demo Mode",
  canViewForecast: true,
  canGenerateForecast: true,
  canViewPipeline: true,
  getToken: guestTokenResolver,
};

export const signedOutSessionSnapshot: SessionSnapshot = {
  isLoaded: true,
  isSignedIn: false,
  userId: null,
  displayName: "Awaiting Sign-In",
  primaryEmail: null,
  role: "viewer",
  roleLabel: "Awaiting Sign-In",
  canViewForecast: false,
  canGenerateForecast: false,
  canViewPipeline: false,
  getToken: guestTokenResolver,
};

/** Indicates whether Clerk keys are configured for this environment. */
export function isClerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
}
