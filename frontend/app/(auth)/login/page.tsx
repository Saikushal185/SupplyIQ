"use client";

import Link from "next/link";
import { Show, SignIn, SignUpButton, UserButton } from "@clerk/nextjs";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-3xl rounded-[32px] border border-white/10 bg-slate-900/80 p-8 shadow-glow">
        <p className="text-xs uppercase tracking-[0.32em] text-cyan-300/80">SupplyIQ</p>
        <h1 className="mt-4 text-4xl font-semibold text-white">Sign in to continue to SupplyIQ.</h1>
        <p className="mt-5 max-w-2xl text-base text-slate-300">
          Use your Clerk account to access the dashboard. If this is your first local run, Clerk may briefly show a
          development-instance claim flow before continuing.
        </p>

        <div className="mt-8 grid gap-4 text-sm text-slate-300 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            Protected routes redirect here when there is no active session
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            Roles still come from Clerk public metadata after sign-in
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            Forecast and pipeline access stays restricted by your role
          </div>
        </div>

        <Show when="signed-out">
          <div className="mt-8 flex justify-center">
            <SignIn path="/login" routing="path" forceRedirectUrl="/" signUpUrl="/login" />
          </div>

          <div className="mt-6 flex items-center justify-center gap-3 text-sm text-slate-300">
            <span>Need an account?</span>
            <SignUpButton>
              <button
                type="button"
                className="rounded-full border border-cyan-300/40 bg-cyan-300/10 px-4 py-2 font-medium text-cyan-200 transition hover:bg-cyan-300/20"
              >
                Create one
              </button>
            </SignUpButton>
          </div>
        </Show>

        <Show when="signed-in">
          <div className="mt-8 flex flex-wrap items-center gap-4 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-emerald-100">
            <UserButton />
            <Link
              href="/dashboard"
              className="inline-flex items-center rounded-full bg-emerald-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
            >
              Go to Dashboard
            </Link>
          </div>
        </Show>
      </div>
    </div>
  );
}
