import type { SessionSnapshot } from "@/types";
import { enrichSessionSnapshot } from "@/lib/roles";

const guestTokenResolver = async (): Promise<string | null> => Promise.resolve(null);

/** Default signed-out session state used before Clerk resolves a session. */
export const guestSessionSnapshot: SessionSnapshot = enrichSessionSnapshot({
  isLoaded: true,
  isSignedIn: false,
  userId: null,
  displayName: "Guest Operator",
  primaryEmail: null,
  role: "viewer",
  roleLabel: "Viewer",
  canViewForecast: false,
  canGenerateForecast: false,
  canViewPipeline: false,
  getToken: guestTokenResolver,
});
