import { useMemo } from "react";
import { CompactAnimalTable, FeedingList, TaskList } from "../components/Lists";
import { Panel } from "../components/Panel";
import { StatusChip, toneForStatus } from "../components/StatusChip";
import type { DashboardSummary, FeedingSchedule, ZooTask } from "../types";
import type { IconName } from "../components/Icon";
import { Icon } from "../components/Icon";

export function DashboardView({
  dashboard,
  feedings,
  tasks
}: {
  dashboard: DashboardSummary | null;
  feedings: FeedingSchedule[];
  tasks: ZooTask[];
}) {
  const recentTasks = useMemo(() => tasks.slice(0, 5), [tasks]);
  const recentFeedings = useMemo(() => feedings.slice(0, 6), [feedings]);

  if (!dashboard) return null;

  const stats: Array<[string, number, IconName, "neutral" | "warning" | "danger"]> = [
    ["Tiere", dashboard.animals_total, "paw", "neutral"],
    ["Offene Aufgaben", dashboard.open_tasks, "check", "warning"],
    ["Faellige Fuetterungen", dashboard.due_feedings, "clock", "neutral"],
    ["Kritische Gesundheit", dashboard.critical_health, "heart", "danger"],
    ["Gehege-Warnungen", dashboard.warning_enclosures, "shield", "warning"]
  ];

  return (
    <div className="view-stack">
      <section className="stat-grid">
        {stats.map(([label, value, icon, tone]) => (
          <article className={`stat-card ${tone}`} key={label}>
            <Icon name={icon} />
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </section>

      <section className="split-grid">
        <Panel title="Gesundheitswarnungen" icon="heart">
          <CompactAnimalTable animals={dashboard.warning_animals} />
        </Panel>
        <Panel title="Naechste Aufgaben" icon="check">
          <TaskList tasks={recentTasks} />
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Fuetterungsplan" icon="clock">
          <FeedingList feedings={recentFeedings} />
        </Panel>
        <Panel title="Gehegestatus" icon="shield">
          <div className="status-list">
            {dashboard.enclosure_status.map((enclosure) => (
              <div className="status-row" key={enclosure.id}>
                <span>{enclosure.name}</span>
                <small>{enclosure.location}</small>
                <StatusChip value={enclosure.safety_status} tone={toneForStatus(enclosure.safety_status)} />
              </div>
            ))}
          </div>
        </Panel>
      </section>
    </div>
  );
}
