import type { ViewKey } from "../constants";
import { useWorkspaceData } from "../hooks/useWorkspaceData";
import type { Session } from "../types";
import { AssignmentsView } from "../views/AssignmentsView";
import { AnimalsView } from "../views/AnimalsView";
import { AuditView } from "../views/AuditView";
import { DashboardView } from "../views/DashboardView";
import { EnclosuresView } from "../views/EnclosuresView";
import { EconomyView } from "../views/EconomyView";
import { FeedingsView } from "../views/FeedingsView";
import { HealthView } from "../views/HealthView";
import { KeeperCalendarView } from "../views/KeeperCalendarView";
import { SpeciesView } from "../views/SpeciesView";
import { TasksView } from "../views/TasksView";
import { VetCalendarView } from "../views/VetCalendarView";
import { VisitorMapView } from "../views/VisitorMapView";
import { Icon } from "./Icon";

export function DataWorkspace({
  session,
  view,
  onUnauthorized
}: {
  session: Session;
  view: ViewKey;
  onUnauthorized: () => void;
}) {
  const data = useWorkspaceData(session, view, onUnauthorized);

  return (
    <section className="content-region" aria-busy={data.isLoading}>
      {data.error ? (
        <div className="notice error">
          <Icon name="alert" />
          <span>{data.error}</span>
          <button type="button" onClick={() => void data.reload()}>
            Erneut laden
          </button>
        </div>
      ) : null}
      {data.isLoading ? <div className="notice">Daten werden geladen...</div> : null}
      {!data.isLoading && view === "dashboard" ? <DashboardView dashboard={data.dashboard} feedings={data.feedings} tasks={data.tasks} /> : null}
      {!data.isLoading && view === "animals" ? (
        <AnimalsView
          session={session}
          animals={data.animals}
          species={data.species}
          enclosures={data.enclosures}
          reload={data.reload}
        />
      ) : null}
      {!data.isLoading && view === "species" ? <SpeciesView session={session} species={data.species} reload={data.reload} /> : null}
      {!data.isLoading && view === "enclosures" ? <EnclosuresView session={session} enclosures={data.enclosures} reload={data.reload} /> : null}
      {!data.isLoading && view === "feedings" ? (
        <FeedingsView session={session} animals={data.animals} feedings={data.feedings} reload={data.reload} />
      ) : null}
      {!data.isLoading && view === "health" ? (
        <HealthView session={session} animals={data.animals} healthRecords={data.healthRecords} reload={data.reload} />
      ) : null}
      {!data.isLoading && view === "tasks" ? (
        <TasksView
          session={session}
          tasks={data.tasks}
          animals={data.animals}
          enclosures={data.enclosures}
          reload={data.reload}
        />
      ) : null}
      {!data.isLoading && view === "assignments" ? (
        <AssignmentsView
          session={session}
          users={data.users}
          animals={data.animals}
          enclosures={data.enclosures}
          animalAssignments={data.animalAssignments}
          enclosureAssignments={data.enclosureAssignments}
          reload={data.reload}
        />
      ) : null}
      {!data.isLoading && view === "keeperCalendar" ? (
        <KeeperCalendarView
          session={session}
          animals={data.animals}
          careTasks={data.careTasks}
          conditionReports={data.conditionReports}
          reload={data.reload}
        />
      ) : null}
      {!data.isLoading && view === "vetCalendar" ? (
        <VetCalendarView
          session={session}
          animals={data.animals}
          vetTasks={data.vetTasks}
          medicalReports={data.medicalReports}
          reload={data.reload}
        />
      ) : null}
      {!data.isLoading && view === "visitorMap" ? <VisitorMapView publicMap={data.publicMap} /> : null}
      {!data.isLoading && view === "economy" ? (
        <EconomyView session={session} economy={data.economy} users={data.users} animals={data.animals} />
      ) : null}
      {!data.isLoading && view === "audit" ? <AuditView auditLogs={data.auditLogs} /> : null}
    </section>
  );
}
