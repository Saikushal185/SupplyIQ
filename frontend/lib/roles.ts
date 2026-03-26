import type { SessionSnapshot, UserRole } from "@/types";

const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrator",
  analyst: "Analyst",
  viewer: "Viewer",
};

export function normalizeUserRole(value: unknown): UserRole {
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized === "admin" || normalized === "analyst" || normalized === "viewer") {
      return normalized;
    }
  }
  return "viewer";
}

export function getRoleLabel(role: UserRole): string {
  return ROLE_LABELS[role];
}

export function canViewForecast(role: UserRole): boolean {
  return role === "admin" || role === "analyst";
}

export function canGenerateForecast(role: UserRole): boolean {
  return role === "admin" || role === "analyst";
}

export function canViewPipeline(role: UserRole): boolean {
  return role === "admin";
}

export function getDefaultRouteForRole(role: UserRole): string {
  if (canViewPipeline(role)) {
    return "/dashboard";
  }
  if (canViewForecast(role)) {
    return "/dashboard";
  }
  return "/dashboard";
}

export function enrichSessionSnapshot(session: SessionSnapshot): SessionSnapshot {
  return {
    ...session,
    roleLabel: getRoleLabel(session.role),
    canViewForecast: canViewForecast(session.role),
    canGenerateForecast: canGenerateForecast(session.role),
    canViewPipeline: canViewPipeline(session.role),
  };
}
