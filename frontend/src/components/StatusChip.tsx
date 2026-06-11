import type { HealthStatus, TaskStatus } from "../types";

export type Tone = "neutral" | "ok" | "warning" | "danger";

export function StatusChip({ value, tone }: { value: string; tone: Tone }) {
  return <span className={`status-chip ${tone}`}>{value}</span>;
}

export function toneForHealth(status: HealthStatus): Tone {
  if (status === "healthy") return "ok";
  if (status === "critical") return "danger";
  return "warning";
}

export function toneForStatus(status: string): Tone {
  if (status === "ok") return "ok";
  if (status === "critical") return "danger";
  if (status === "warning") return "warning";
  return "neutral";
}

export function toneForTask(status: TaskStatus): Tone {
  if (status === "done") return "ok";
  if (status === "in_progress") return "neutral";
  return "warning";
}
