export type Role = "admin" | "keeper" | "vet" | "viewer";
export type SafetyStatus = "ok" | "warning" | "critical";
export type HealthStatus = "healthy" | "observation" | "treatment" | "critical";
export type Sex = "male" | "female" | "unknown";
export type TaskStatus = "open" | "in_progress" | "done";
export type TaskType = "feeding" | "cleaning" | "checkup" | "maintenance";
export type RecordType = "checkup" | "medication" | "incident" | "note";

export interface Session {
  role: Role;
  display_name: string;
  csrf_token: string;
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
}

export interface Species {
  id: number;
  common_name: string;
  scientific_name?: string | null;
  category: string;
  conservation_status?: string | null;
  husbandry_notes?: string | null;
}

export interface Enclosure {
  id: number;
  name: string;
  location: string;
  capacity: number;
  safety_status: SafetyStatus;
  notes?: string | null;
}

export interface Animal {
  id: number;
  name: string;
  species_id: number;
  enclosure_id: number;
  birth_date?: string | null;
  sex: Sex;
  health_status: HealthStatus;
  active: boolean;
  created_at: string;
  updated_at: string;
  species: Species;
  enclosure: Enclosure;
}

export interface FeedingSchedule {
  id: number;
  animal_id: number;
  food_type: string;
  amount: string;
  scheduled_time: string;
  recurrence: string;
  responsible_role: Role;
  notes?: string | null;
  animal: Animal;
}

export interface HealthRecord {
  id: number;
  animal_id: number;
  record_type: RecordType;
  description: string;
  medication?: string | null;
  next_check_date?: string | null;
  created_by_user_id: number;
  created_at: string;
  animal: Animal;
  created_by: User;
}

export interface ZooTask {
  id: number;
  title: string;
  description?: string | null;
  task_type: TaskType;
  assigned_role: Role;
  due_at: string;
  status: TaskStatus;
  related_animal_id?: number | null;
  related_enclosure_id?: number | null;
}

export interface AuditLog {
  id: number;
  actor_user_id?: number | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  timestamp: string;
  ip_hash?: string | null;
  details?: Record<string, unknown> | null;
}

export interface DashboardSummary {
  animals_total: number;
  open_tasks: number;
  due_feedings: number;
  critical_health: number;
  warning_enclosures: number;
  recent_tasks: ZooTask[];
  warning_animals: Animal[];
  enclosure_status: Enclosure[];
}
