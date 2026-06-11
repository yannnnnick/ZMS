import type { HealthStatus, Role } from "./types";
import type { IconName } from "./components/Icon";

export type ViewKey =
  | "dashboard"
  | "animals"
  | "species"
  | "enclosures"
  | "feedings"
  | "health"
  | "tasks"
  | "assignments"
  | "keeperCalendar"
  | "vetCalendar"
  | "visitorMap"
  | "economy"
  | "audit";

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
  { key: "dashboard", label: "Dashboard", icon: "grid", roles: ["admin", "keeper", "vet"] },
  { key: "keeperCalendar", label: "Pflegekalender", icon: "calendar", roles: ["keeper"] },
  { key: "vetCalendar", label: "Vet-Kalender", icon: "heart", roles: ["vet"] },
  { key: "animals", label: "Tiere", icon: "paw", roles: ["admin", "keeper", "vet"] },
  { key: "species", label: "Arten", icon: "leaf", roles: ["admin", "keeper", "vet"] },
  { key: "enclosures", label: "Gehege", icon: "shield", roles: ["admin", "keeper", "vet"] },
  { key: "feedings", label: "Fuetterungsplaene", icon: "clock", roles: ["admin", "keeper", "vet"] },
  { key: "health", label: "Gesundheit", icon: "heart", roles: ["admin", "vet"] },
  { key: "tasks", label: "Aufgaben", icon: "check", roles: ["admin", "keeper", "vet"] },
  { key: "assignments", label: "Zuweisungen", icon: "users", roles: ["admin"] },
  { key: "economy", label: "Wirtschaft", icon: "chart", roles: ["admin"] },
  { key: "visitorMap", label: "Besucherkarte", icon: "map", roles: ["viewer"] },
  { key: "audit", label: "Audit", icon: "file", roles: ["admin"] }
];
