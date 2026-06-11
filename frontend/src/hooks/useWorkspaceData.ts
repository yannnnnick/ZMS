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
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
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

    try {
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
        needsCoreData ? api.dashboard() : Promise.resolve(null),
        needsCoreData || needsAssignments || needsCare || needsVet || needsEconomy ? api.animals() : Promise.resolve([] as Animal[]),
        needsCoreData ? api.species() : Promise.resolve([] as Species[]),
        needsCoreData || needsAssignments ? api.enclosures() : Promise.resolve([] as Enclosure[]),
        canUsePrivilegedOps ? api.tasks() : Promise.resolve([] as ZooTask[]),
        needsFeedings ? api.feedings() : Promise.resolve([] as FeedingSchedule[]),
        needsHealth ? api.healthRecords() : Promise.resolve([] as HealthRecord[]),
        needsAssignments || needsEconomy ? api.users() : Promise.resolve([] as User[]),
        needsAssignments ? api.animalAssignments() : Promise.resolve([] as AnimalAssignment[]),
        needsAssignments ? api.enclosureAssignments() : Promise.resolve([] as EnclosureAssignment[]),
        needsCare ? api.careTasks() : Promise.resolve([] as CareTask[]),
        needsCare ? api.conditionReports() : Promise.resolve([] as AnimalConditionReport[]),
        needsVet ? api.vetTasks() : Promise.resolve([] as VetTask[]),
        needsVet ? api.medicalReports() : Promise.resolve([] as MedicalReport[]),
        needsPublicMap ? api.publicMap() : Promise.resolve(null),
        needsEconomy ? api.economy() : Promise.resolve(null),
        needsAudit ? api.auditLogs() : Promise.resolve([] as AuditLog[])
      ]);

      if (requestId !== requestIdRef.current) return;
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
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof ApiError ? err.message : "Backend nicht erreichbar");
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
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
