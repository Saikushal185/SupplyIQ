import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";

const protectedPrefixes = ["/dashboard", "/analytics", "/forecast", "/pipeline"];

/** Integrates Clerk request context with route redirects for protected pages. */
export default clerkMiddleware(async (auth, request: NextRequest) => {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  if (!clerkEnabled) {
    return NextResponse.next();
  }

  const pathname = request.nextUrl.pathname;
  const isProtectedRoute = protectedPrefixes.some((prefix) => pathname.startsWith(prefix));
  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  const { userId } = await auth();
  if (userId) {
    return NextResponse.next();
  }

  const redirectUrl = new URL("/login", request.url);
  redirectUrl.searchParams.set("redirect_url", `${pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(redirectUrl);
});

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/analytics/:path*",
    "/forecast/:path*",
    "/pipeline/:path*",
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
