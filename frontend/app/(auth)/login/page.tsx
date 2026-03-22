import { isClerkConfigured } from "@/lib/auth";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-lg rounded-3xl border border-white/10 bg-slate-900/80 p-8 shadow-glow">
        <p className="text-xs uppercase tracking-[0.3em] text-teal-300/80">SupplyIQ</p>
        <h1 className="mt-4 text-3xl font-semibold text-white">Login Surface</h1>
        <p className="mt-4 text-slate-300">
          {isClerkConfigured()
            ? "Clerk publishable key is configured. Add your chosen auth flow wiring here before enabling protected routes."
            : "Clerk environment variables are not configured yet. This page is ready for provider wiring without changing the route structure."}
        </p>
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-5">
          <p className="text-sm text-slate-300">
            Recommended next step: wire Clerk sign-in UI here and pair it with backend JWT verification before enabling route protection.
          </p>
        </div>
      </div>
    </div>
  );
}
