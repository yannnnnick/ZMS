import type { HealthStatus, Role } from "./types";
import type { IconName } from "./components/Icon";

export type ViewKey = "dashboard" | "animals" | "species" | "enclosures" | "feedings" | "health" | "tasks" | "audit";

export const csrfCookieName = "zms_csrf_token";

export const roleLabels: Record<Role, string> = {
  admin: "Admin",
  keeper: "Keeper",
  vet: "Vet",
  viewer: "Viewer"
};

export const healthLabels: Record<HealthStatus, string> = {
  healthy: "Gesund",
  observation: "Beobachtung",
  treatment: "Behandlung",
  critical: "Kritisch"
};

export const navItems: Array<{ key: ViewKey; label: string; icon: IconName; roles?: Role[] }> = [
  { key: "dashboard", label: "Dashboard", icon: "grid" },
  { key: "animals", label: "Tiere", icon: "paw" },
  { key: "species", label: "Arten", icon: "leaf" },
  { key: "enclosures", label: "Gehege", icon: "shield" },
  { key: "feedings", label: "Fuetterungsplaene", icon: "clock", roles: ["admin", "keeper", "vet"] },
  { key: "health", label: "Gesundheit", icon: "heart", roles: ["admin", "vet"] },
  { key: "tasks", label: "Aufgaben", icon: "check", roles: ["admin", "keeper", "vet"] },
  { key: "audit", label: "Audit", icon: "file", roles: ["admin"] }
];
