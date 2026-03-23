import type { SessionSnapshot } from "@/types";

const guestTokenResolver = async (): Promise<string | null> => Promise.resolve(null);

export const guestSessionSnapshot: SessionSnapshot = {
  isLoaded: true,
  isSignedIn: false,
  userId: null,
  displayName: "Guest Operator",
  primaryEmail: null,
  roleLabel: "Demo Mode",
  getToken: guestTokenResolver,
};

/** Indicates whether Clerk keys are configured for this environment. */
export function isClerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
}
