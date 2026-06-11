import type {
  Animal,
  AuditLog,
  DashboardSummary,
  Enclosure,
  FeedingSchedule,
  HealthRecord,
  Session,
  Species,
  User,
  ZooTask
} from "./types";

function normalizeApiBase(value: string | undefined): string {
  const base = value?.trim() || "/api";
  if (base === "/") return "";
  return base.replace(/\/+$/, "");
}

const API_BASE = normalizeApiBase(import.meta.env.VITE_API_URL);
const REQUEST_TIMEOUT_MS = 10_000;

type RequestOptions = RequestInit & {
  csrfToken?: string;
  timeoutMs?: number;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function messageFromDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => {
        if (typeof entry === "object" && entry && "msg" in entry) {
          return String(entry.msg);
        }
        return String(entry);
      })
      .join("; ");
  }
  return "Request failed";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { csrfToken, headers, timeoutMs = REQUEST_TIMEOUT_MS, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  const requestHeaders = new Headers(headers);

  if (fetchOptions.body && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }
  if (csrfToken) {
    requestHeaders.set("X-CSRF-Token", csrfToken);
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      credentials: "include",
      headers: requestHeaders,
      signal: controller.signal
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new ApiError(response.status, messageFromDetail(body.detail));
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "Zeitueberschreitung beim API-Aufruf");
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export const api = {
  login: (email: string, password: string) =>
    request<Session>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: (csrfToken: string) => request<{ status: string }>("/auth/logout", { method: "POST", csrfToken }),
  me: () => request<User>("/me"),
  dashboard: () => request<DashboardSummary>("/dashboard"),
  animals: () => request<Animal[]>("/animals"),
  createAnimal: (csrfToken: string, body: Record<string, unknown>) =>
    request<Animal>("/animals", { method: "POST", csrfToken, body: JSON.stringify(body) }),
  updateAnimal: (csrfToken: string, id: number, body: Record<string, unknown>) =>
    request<Animal>(`/animals/${id}`, { method: "PATCH", csrfToken, body: JSON.stringify(body) }),
  deleteAnimal: (csrfToken: string, id: number) => request<void>(`/animals/${id}`, { method: "DELETE", csrfToken }),
  species: () => request<Species[]>("/species"),
  createSpecies: (csrfToken: string, body: Record<string, unknown>) =>
    request<Species>("/species", { method: "POST", csrfToken, body: JSON.stringify(body) }),
  enclosures: () => request<Enclosure[]>("/enclosures"),
  createEnclosure: (csrfToken: string, body: Record<string, unknown>) =>
    request<Enclosure>("/enclosures", { method: "POST", csrfToken, body: JSON.stringify(body) }),
  feedings: () => request<FeedingSchedule[]>("/feeding-schedules"),
  createFeeding: (csrfToken: string, body: Record<string, unknown>) =>
    request<FeedingSchedule>("/feeding-schedules", { method: "POST", csrfToken, body: JSON.stringify(body) }),
  healthRecords: () => request<HealthRecord[]>("/health-records"),
  createHealthRecord: (csrfToken: string, body: Record<string, unknown>) =>
    request<HealthRecord>("/health-records", { method: "POST", csrfToken, body: JSON.stringify(body) }),
  tasks: () => request<ZooTask[]>("/tasks"),
  createTask: (csrfToken: string, body: Record<string, unknown>) =>
    request<ZooTask>("/tasks", { method: "POST", csrfToken, body: JSON.stringify(body) }),
  updateTask: (csrfToken: string, id: number, body: Record<string, unknown>) =>
    request<ZooTask>(`/tasks/${id}`, { method: "PATCH", csrfToken, body: JSON.stringify(body) }),
  deleteTask: (csrfToken: string, id: number) => request<void>(`/tasks/${id}`, { method: "DELETE", csrfToken }),
  auditLogs: () => request<AuditLog[]>("/audit-logs")
};
