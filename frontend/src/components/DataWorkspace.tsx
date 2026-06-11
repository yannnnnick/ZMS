import type { ViewKey } from "../constants";
import { useWorkspaceData } from "../hooks/useWorkspaceData";
import type { Session } from "../types";
import { AnimalsView } from "../views/AnimalsView";
import { AuditView } from "../views/AuditView";
import { DashboardView } from "../views/DashboardView";
import { EnclosuresView } from "../views/EnclosuresView";
import { FeedingsView } from "../views/FeedingsView";
import { HealthView } from "../views/HealthView";
import { SpeciesView } from "../views/SpeciesView";
import { TasksView } from "../views/TasksView";
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
      {!data.isLoading && view === "audit" ? <AuditView auditLogs={data.auditLogs} /> : null}
    </section>
  );
}
