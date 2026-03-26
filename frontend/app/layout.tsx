import type { Metadata } from "next";
import { ClerkProvider, Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";

import "@/app/globals.css";
import { AppProviders } from "@/components/providers/AppProviders";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "SupplyIQ",
  description: "AI-powered supply chain intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ClerkProvider>
          <header className="flex items-center justify-end gap-3 border-b border-white/10 bg-slate-950/90 px-4 py-4 backdrop-blur lg:px-6">
            <Show when="signed-out">
              <SignInButton>
                <button
                  type="button"
                  className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
                >
                  Sign In
                </button>
              </SignInButton>
              <SignUpButton>
                <button
                  type="button"
                  className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
                >
                  Sign Up
                </button>
              </SignUpButton>
            </Show>
            <Show when="signed-in">
              <UserButton />
            </Show>
          </header>

          <AppProviders>
            <AppShell>{children}</AppShell>
          </AppProviders>
        </ClerkProvider>
      </body>
    </html>
  );
}
