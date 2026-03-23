import { NextResponse, type NextRequest } from "next/server";

const protectedPrefixes = ["/dashboard", "/analytics", "/forecast"];

/** Protects app routes in middleware when Clerk session cookies are available. */
export function middleware(request: NextRequest) {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (!clerkEnabled) {
    return NextResponse.next();
  }

  const pathname = request.nextUrl.pathname;
  const isProtectedRoute = protectedPrefixes.some((prefix) => pathname.startsWith(prefix));
  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  const hasSessionCookie = Boolean(request.cookies.get("__session")?.value);
  if (hasSessionCookie) {
    return NextResponse.next();
  }

  const redirectUrl = new URL("/login", request.url);
  redirectUrl.searchParams.set("redirect_url", pathname);
  return NextResponse.redirect(redirectUrl);
}

export const config = {
  matcher: ["/dashboard/:path*", "/analytics/:path*", "/forecast/:path*"],
};
