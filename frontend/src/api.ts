import type {
  Animal,
  AuditLog,
  DashboardSummary,
  Enclosure,
  FeedingSchedule,
  HealthRecord,
  Session,
  Species,
  ZooTask
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

type RequestOptions = RequestInit & { token?: string };

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers, ...fetchOptions } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers
    }
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new ApiError(response.status, body.detail ?? "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<Session>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: (token: string) => request<{ status: string }>("/auth/logout", { method: "POST", token }),
  dashboard: (token: string) => request<DashboardSummary>("/dashboard", { token }),
  animals: (token: string) => request<Animal[]>("/animals", { token }),
  createAnimal: (token: string, body: Record<string, unknown>) =>
    request<Animal>("/animals", { method: "POST", token, body: JSON.stringify(body) }),
  updateAnimal: (token: string, id: number, body: Record<string, unknown>) =>
    request<Animal>(`/animals/${id}`, { method: "PATCH", token, body: JSON.stringify(body) }),
  deleteAnimal: (token: string, id: number) => request<void>(`/animals/${id}`, { method: "DELETE", token }),
  species: (token: string) => request<Species[]>("/species", { token }),
  createSpecies: (token: string, body: Record<string, unknown>) =>
    request<Species>("/species", { method: "POST", token, body: JSON.stringify(body) }),
  enclosures: (token: string) => request<Enclosure[]>("/enclosures", { token }),
  createEnclosure: (token: string, body: Record<string, unknown>) =>
    request<Enclosure>("/enclosures", { method: "POST", token, body: JSON.stringify(body) }),
  feedings: (token: string) => request<FeedingSchedule[]>("/feeding-schedules", { token }),
  createFeeding: (token: string, body: Record<string, unknown>) =>
    request<FeedingSchedule>("/feeding-schedules", { method: "POST", token, body: JSON.stringify(body) }),
  healthRecords: (token: string) => request<HealthRecord[]>("/health-records", { token }),
  createHealthRecord: (token: string, body: Record<string, unknown>) =>
    request<HealthRecord>("/health-records", { method: "POST", token, body: JSON.stringify(body) }),
  tasks: (token: string) => request<ZooTask[]>("/tasks", { token }),
  createTask: (token: string, body: Record<string, unknown>) =>
    request<ZooTask>("/tasks", { method: "POST", token, body: JSON.stringify(body) }),
  updateTask: (token: string, id: number, body: Record<string, unknown>) =>
    request<ZooTask>(`/tasks/${id}`, { method: "PATCH", token, body: JSON.stringify(body) }),
  auditLogs: (token: string) => request<AuditLog[]>("/audit-logs", { token })
};

