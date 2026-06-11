export type Role = "admin" | "keeper" | "vet" | "viewer";
export type SafetyStatus = "ok" | "warning" | "critical";
export type HealthStatus = "healthy" | "observation" | "treatment" | "critical";
export type Sex = "male" | "female" | "unknown";
export type TaskStatus = "open" | "in_progress" | "done";
export type TaskType = "feeding" | "cleaning" | "checkup" | "maintenance";
export type RecordType = "checkup" | "medication" | "incident" | "note";
export type AssignmentRoleType = "keeper" | "vet";
export type CareTaskType = "feeding" | "cleaning" | "health_check" | "enrichment" | "custom";
export type CareTaskStatus = "open" | "done" | "missed";
export type Mood = "normal" | "nervous" | "aggressive" | "tired" | "playful";
export type Appetite = "normal" | "low" | "high" | "refused";
export type Movement = "normal" | "limping" | "weak" | "hyperactive";
export type VetTaskPriority = "low" | "medium" | "high" | "emergency";
export type VetTaskStatus = "open" | "done" | "cancelled";

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
  map_x?: number | null;
  map_y?: number | null;
  map_width?: number | null;
  map_height?: number | null;
  public_name?: string | null;
  public_description?: string | null;
  is_public_visible: boolean;
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
  age_years?: number | null;
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

export interface AnimalAssignment {
  id: number;
  animal_id: number;
  user_id: number;
  role_type: AssignmentRoleType;
  created_at: string;
  active: boolean;
  animal: Animal;
  user: User;
}

export interface EnclosureAssignment {
  id: number;
  enclosure_id: number;
  user_id: number;
  created_at: string;
  active: boolean;
  enclosure: Enclosure;
  user: User;
}

export interface CareTask {
  id: number;
  title: string;
  description?: string | null;
  animal_id?: number | null;
  enclosure_id?: number | null;
  assigned_to_user_id: number;
  task_type: CareTaskType;
  due_date: string;
  due_time?: string | null;
  status: CareTaskStatus;
  completed_at?: string | null;
  created_by: number;
  created_at: string;
  animal?: Animal | null;
  enclosure?: Enclosure | null;
  assigned_to: User;
}

export interface AnimalConditionReport {
  id: number;
  animal_id: number;
  task_id?: number | null;
  mood: Mood;
  appetite: Appetite;
  movement: Movement;
  visible_injuries: boolean;
  notes?: string | null;
  needs_vet_check: boolean;
  created_by_user_id: number;
  created_at: string;
  animal: Animal;
  created_by: User;
}

export interface VetTask {
  id: number;
  title: string;
  description?: string | null;
  animal_id: number;
  assigned_to_user_id: number;
  priority: VetTaskPriority;
  due_date: string;
  status: VetTaskStatus;
  created_by: number;
  created_at: string;
  animal: Animal;
  assigned_to: User;
}

export interface MedicalReport {
  id: number;
  animal_id: number;
  task_id?: number | null;
  diagnosis: string;
  treatment?: string | null;
  medication?: string | null;
  follow_up_required: boolean;
  follow_up_date?: string | null;
  notes?: string | null;
  vet_user_id: number;
  created_at: string;
  animal: Animal;
  vet: User;
}

export interface PublicAnimal {
  name: string;
  species: string;
  sex: Sex;
  age_years?: number | null;
}

export interface PublicEnclosure {
  public_name: string;
  public_description?: string | null;
  location: string;
  map_x: number;
  map_y: number;
  map_width: number;
  map_height: number;
  animals: PublicAnimal[];
}

export interface PublicMapPath {
  from_enclosure: string;
  to_enclosure: string;
  distance_meters?: number | null;
  walking_time_minutes?: number | null;
  path_svg_data?: string | null;
}

export interface PublicZooMap {
  enclosures: PublicEnclosure[];
  paths: PublicMapPath[];
}

export interface VisitorStat {
  date: string;
  visitor_count: number;
  ticket_revenue: number;
}

export interface EconomySummary {
  visitors_today: number;
  visitors_week: number;
  ticket_revenue_week: number;
  estimated_payroll_month: number;
  food_inventory_value: number;
  open_tasks: number;
  open_vet_cases: number;
  visitor_stats: VisitorStat[];
}

export interface SalarySimulation {
  user: User;
  hours: number;
  hourly_rate: number;
  gross_pay: number;
  estimated_deductions: number;
  estimated_net: number;
  is_simulation: boolean;
}

export interface FeedingOptimizationItem {
  food_item_id: number;
  food_name: string;
  quantity: number;
  unit: string;
  cost: number;
}

export interface FeedingOptimization {
  success: boolean;
  message: string;
  total_cost: number;
  feeding_plan: FeedingOptimizationItem[];
  method: string;
}
