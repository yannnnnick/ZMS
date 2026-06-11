import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import type { ViewKey } from "../constants";
import type {
  Animal,
  AnimalAssignment,
  AnimalConditionReport,
  AuditLog,
  CareTask,
  DashboardSummary,
  Enclosure,
  EnclosureAssignment,
  EconomySummary,
  FeedingSchedule,
  HealthRecord,
  MedicalReport,
  PublicZooMap,
  Session,
  Species,
  User,
  VetTask,
  ZooTask
} from "../types";

export interface WorkspaceData {
  dashboard: DashboardSummary | null;
  animals: Animal[];
  species: Species[];
  enclosures: Enclosure[];
  feedings: FeedingSchedule[];
  healthRecords: HealthRecord[];
  tasks: ZooTask[];
  users: User[];
  animalAssignments: AnimalAssignment[];
  enclosureAssignments: EnclosureAssignment[];
  careTasks: CareTask[];
  conditionReports: AnimalConditionReport[];
  vetTasks: VetTask[];
  medicalReports: MedicalReport[];
  publicMap: PublicZooMap | null;
  economy: EconomySummary | null;
  auditLogs: AuditLog[];
  error: string | null;
  isLoading: boolean;
  reload: () => Promise<void>;
}

export function useWorkspaceData(session: Session, view: ViewKey, onUnauthorized: () => void): WorkspaceData {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [species, setSpecies] = useState<Species[]>([]);
  const [enclosures, setEnclosures] = useState<Enclosure[]>([]);
  const [feedings, setFeedings] = useState<FeedingSchedule[]>([]);
  const [healthRecords, setHealthRecords] = useState<HealthRecord[]>([]);
  const [tasks, setTasks] = useState<ZooTask[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [animalAssignments, setAnimalAssignments] = useState<AnimalAssignment[]>([]);
  const [enclosureAssignments, setEnclosureAssignments] = useState<EnclosureAssignment[]>([]);
  const [careTasks, setCareTasks] = useState<CareTask[]>([]);
  const [conditionReports, setConditionReports] = useState<AnimalConditionReport[]>([]);
  const [vetTasks, setVetTasks] = useState<VetTask[]>([]);
  const [medicalReports, setMedicalReports] = useState<MedicalReport[]>([]);
  const [publicMap, setPublicMap] = useState<PublicZooMap | null>(null);
  const [economy, setEconomy] = useState<EconomySummary | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const requestIdRef = useRef(0);

  const loadData = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setError(null);
    setIsLoading(true);

    const canUsePrivilegedOps = ["admin", "keeper", "vet"].includes(session.role);
    const needsCoreData = canUsePrivilegedOps && view !== "visitorMap";
    const needsFeedings = ["feedings", "dashboard"].includes(view) && canUsePrivilegedOps;
    const needsHealth = ["health", "dashboard"].includes(view) && ["admin", "vet"].includes(session.role);
    const needsAssignments = view === "assignments" && session.role === "admin";
    const needsCare = view === "keeperCalendar" && session.role === "keeper";
    const needsVet = view === "vetCalendar" && session.role === "vet";
    const needsPublicMap = view === "visitorMap";
    const needsEconomy = view === "economy" && session.role === "admin";
    const needsAudit = view === "audit" && session.role === "admin";

    // Each request is settled independently: a single failing endpoint degrades only its
    // own slice of the workspace instead of blanking everything (as Promise.all would).
    // A 401 anywhere still means the session is gone, so it is surfaced separately.
    const failures: string[] = [];
    let unauthorized = false;
    const settle = async <T,>(active: boolean, call: () => Promise<T>, fallback: T): Promise<T> => {
      if (!active) return fallback;
      try {
        return await call();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          unauthorized = true;
        } else {
          failures.push(err instanceof ApiError ? err.message : "Backend nicht erreichbar");
        }
        return fallback;
      }
    };

    const [
      dashboardData,
      animalData,
      speciesData,
      enclosureData,
      taskData,
      feedingData,
      healthData,
      userData,
      animalAssignmentData,
      enclosureAssignmentData,
      careTaskData,
      conditionReportData,
      vetTaskData,
      medicalReportData,
      publicMapData,
      economyData,
      auditData
    ] = await Promise.all([
      settle(needsCoreData, api.dashboard, null as DashboardSummary | null),
      settle(needsCoreData || needsAssignments || needsCare || needsVet || needsEconomy, api.animals, [] as Animal[]),
      settle(needsCoreData, api.species, [] as Species[]),
      settle(needsCoreData || needsAssignments, api.enclosures, [] as Enclosure[]),
      settle(canUsePrivilegedOps, api.tasks, [] as ZooTask[]),
      settle(needsFeedings, api.feedings, [] as FeedingSchedule[]),
      settle(needsHealth, api.healthRecords, [] as HealthRecord[]),
      settle(needsAssignments || needsEconomy, api.users, [] as User[]),
      settle(needsAssignments, api.animalAssignments, [] as AnimalAssignment[]),
      settle(needsAssignments, api.enclosureAssignments, [] as EnclosureAssignment[]),
      settle(needsCare, api.careTasks, [] as CareTask[]),
      settle(needsCare, api.conditionReports, [] as AnimalConditionReport[]),
      settle(needsVet, api.vetTasks, [] as VetTask[]),
      settle(needsVet, api.medicalReports, [] as MedicalReport[]),
      settle(needsPublicMap, api.publicMap, null as PublicZooMap | null),
      settle(needsEconomy, api.economy, null as EconomySummary | null),
      settle(needsAudit, api.auditLogs, [] as AuditLog[])
    ]);

    if (requestId !== requestIdRef.current) return;
    setIsLoading(false);
    if (unauthorized) {
      onUnauthorized();
      return;
    }

    setDashboard(dashboardData);
    setAnimals(animalData);
    setSpecies(speciesData);
    setEnclosures(enclosureData);
    setTasks(taskData);
    setFeedings(feedingData);
    setHealthRecords(healthData);
    setUsers(userData);
    setAnimalAssignments(animalAssignmentData);
    setEnclosureAssignments(enclosureAssignmentData);
    setCareTasks(careTaskData);
    setConditionReports(conditionReportData);
    setVetTasks(vetTaskData);
    setMedicalReports(medicalReportData);
    setPublicMap(publicMapData);
    setEconomy(economyData);
    setAuditLogs(auditData);
    setError(failures.length ? failures[0] : null);
  }, [onUnauthorized, session.role, view]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return {
    dashboard,
    animals,
    species,
    enclosures,
    feedings,
    healthRecords,
    tasks,
    users,
    animalAssignments,
    enclosureAssignments,
    careTasks,
    conditionReports,
    vetTasks,
    medicalReports,
    publicMap,
    economy,
    auditLogs,
    error,
    isLoading,
    reload: loadData
  };
}
