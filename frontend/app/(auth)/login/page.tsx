import { SignIn } from "@clerk/nextjs";

import { isClerkConfigured } from "@/lib/auth-config";

function LogoMark() {
  return (
    <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[28px] bg-gradient-to-br from-indigo-500 to-cyan-500 text-2xl font-semibold text-white shadow-glow">
      SI
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <div className="w-full max-w-lg text-center">
        <LogoMark />
        <p className="eyebrow mt-6">SupplyIQ</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-white">Sign in to the control tower</h1>
        <p className="mt-4 text-base text-slate-300">
          Forecast demand, monitor inventory risk, and keep every region aligned from one secure workspace.
        </p>

        <div className="panel-surface mt-8 overflow-hidden p-6 sm:p-8">
          {isClerkConfigured() ? (
            <div className="flex justify-center">
              <SignIn path="/login" routing="path" fallbackRedirectUrl="/dashboard" />
            </div>
          ) : (
            <div className="space-y-5 text-left">
              <div className="rounded-[24px] border border-cyan-400/15 bg-cyan-400/10 p-5">
                <p className="text-xs uppercase tracking-[0.28em] text-cyan-100/80">Authentication Ready</p>
                <p className="mt-3 text-sm text-slate-200">
                  Clerk is wired into the app shell, middleware, and session context. Add the matching keys below to enable protected sign-in.
                </p>
              </div>
              <div className="rounded-[24px] border border-white/10 bg-slate-950/45 p-5">
                <p className="text-sm font-medium text-white">Required environment variables</p>
                <ul className="mt-4 space-y-3 text-sm text-slate-300">
                  <li className="mono-data">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</li>
                  <li className="mono-data">CLERK_SECRET_KEY</li>
                  <li className="mono-data">BACKEND_CLERK_JWKS_URL</li>
                  <li className="mono-data">BACKEND_CLERK_ISSUER</li>
                  <li className="mono-data">BACKEND_AUTH_ENABLED=true</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
