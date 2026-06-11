import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import type { ViewKey } from "../constants";
import type { Animal, AuditLog, DashboardSummary, Enclosure, FeedingSchedule, HealthRecord, Session, Species, ZooTask } from "../types";

export interface WorkspaceData {
  dashboard: DashboardSummary | null;
  animals: Animal[];
  species: Species[];
  enclosures: Enclosure[];
  feedings: FeedingSchedule[];
  healthRecords: HealthRecord[];
  tasks: ZooTask[];
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
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const requestIdRef = useRef(0);

  const loadData = useCallback(async () => {
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setError(null);
    setIsLoading(true);

    const canUsePrivilegedOps = session.role !== "viewer";
    const needsFeedings = ["feedings", "dashboard"].includes(view) && canUsePrivilegedOps;
    const needsHealth = ["health", "dashboard"].includes(view) && ["admin", "vet"].includes(session.role);
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
        auditData
      ] = await Promise.all([
        api.dashboard(),
        api.animals(),
        api.species(),
        api.enclosures(),
        canUsePrivilegedOps ? api.tasks() : Promise.resolve([] as ZooTask[]),
        needsFeedings ? api.feedings() : Promise.resolve([] as FeedingSchedule[]),
        needsHealth ? api.healthRecords() : Promise.resolve([] as HealthRecord[]),
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
    auditLogs,
    error,
    isLoading,
    reload: loadData
  };
}
