/** Indicates whether Clerk is configured for this environment. */
export function isClerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
}

/** Returns a placeholder token value until Clerk runtime integration is enabled. */
export async function getServerSessionToken(): Promise<string | null> {
  return Promise.resolve(null);
}
