import { api } from "../api";
import { healthLabels } from "../constants";
import type { Animal, FeedingSchedule, ZooTask } from "../types";
import { Icon } from "./Icon";
import { StatusChip, toneForHealth, toneForTask } from "./StatusChip";

export function CompactAnimalTable({ animals }: { animals: Animal[] }) {
  if (!animals.length) return <p className="empty-state">Keine Warnungen.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Tier</th>
            <th>Art</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {animals.map((animal) => (
            <tr key={animal.id}>
              <td>{animal.name}</td>
              <td>{animal.species.common_name}</td>
              <td>
                <StatusChip value={healthLabels[animal.health_status]} tone={toneForHealth(animal.health_status)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TaskList({
  tasks,
  csrfToken,
  canEdit = false,
  reload
}: {
  tasks: ZooTask[];
  csrfToken?: string;
  canEdit?: boolean;
  reload?: () => Promise<void>;
}) {
  if (!tasks.length) return <p className="empty-state">Keine Aufgaben.</p>;
  return (
    <div className="status-list">
      {tasks.map((task) => (
        <div className="status-row" key={task.id}>
          <span>{task.title}</span>
          <small>{new Date(task.due_at).toLocaleString("de-DE")}</small>
          <StatusChip value={task.status} tone={toneForTask(task.status)} />
          {canEdit && csrfToken && reload && task.status !== "done" ? (
            <button
              className="icon-button"
              title="Erledigen"
              type="button"
              onClick={async () => {
                await api.updateTask(csrfToken, task.id, { status: "done" });
                await reload();
              }}
            >
              <Icon name="check" />
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function FeedingList({ feedings }: { feedings: FeedingSchedule[] }) {
  if (!feedings.length) return <p className="empty-state">Keine Fuetterungen geladen.</p>;
  return (
    <div className="status-list">
      {feedings.map((feeding) => (
        <div className="status-row" key={feeding.id}>
          <span>{feeding.animal.name}</span>
          <small>
            {feeding.scheduled_time.slice(0, 5)} - {feeding.food_type} - {feeding.amount}
          </small>
          <StatusChip value={feeding.recurrence} tone="neutral" />
        </div>
      ))}
    </div>
  );
}
