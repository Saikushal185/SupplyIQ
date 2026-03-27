import { SignIn } from "@clerk/nextjs";

import { isClerkConfigured } from "@/lib/auth-config";

export default function LoginPage() {
  if (!isClerkConfigured()) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-xl rounded-3xl border border-white/10 bg-slate-900/80 p-8 shadow-glow">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">SupplyIQ</p>
          <h1 className="mt-4 text-3xl font-semibold text-white">Authentication Ready</h1>
          <p className="mt-4 text-slate-300">
            Clerk is now wired into the app shell, session context, and route middleware. Add your Clerk publishable
            key to [frontend/.env] and matching backend JWKS settings to enable protected runtime sign-in.
          </p>
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="text-sm text-slate-300">Required env vars:</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-400">
              <li>`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`</li>
              <li>`CLERK_SECRET_KEY`</li>
              <li>`BACKEND_CLERK_JWKS_URL`</li>
              <li>`BACKEND_CLERK_ISSUER`</li>
              <li>`BACKEND_AUTH_ENABLED=true`</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-5xl overflow-hidden rounded-[32px] border border-white/10 bg-slate-900/80 shadow-glow">
        <div className="grid min-h-[680px] lg:grid-cols-[1.05fr_minmax(0,0.95fr)]">
          <div className="relative overflow-hidden border-b border-white/10 p-8 lg:border-b-0 lg:border-r">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(45,212,191,0.14),transparent_28%)]" />
            <div className="relative">
              <p className="text-xs uppercase tracking-[0.32em] text-cyan-300/80">SupplyIQ</p>
              <h1 className="mt-4 max-w-md text-4xl font-semibold text-white">Secure your supply chain control tower.</h1>
              <p className="mt-5 max-w-lg text-base text-slate-300">
                Sign in to monitor supplier risk, generate forecasts, and action inventory interventions from a single
                operations workspace.
              </p>
              <div className="mt-10 grid gap-4 text-sm text-slate-300">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  Protected App Router middleware for dashboard, analytics, forecast, and pipeline routes
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  Clerk session context feeding SWR data access and backend bearer token requests
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  Backend JWT verification ready for protected FastAPI routes
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center p-8">
            <SignIn path="/login" routing="path" fallbackRedirectUrl="/dashboard" />
          </div>
        </div>
      </div>
    </div>
  );
}
