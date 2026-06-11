import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { StatusChip } from "../components/StatusChip";
import type { Animal, AnimalConditionReport, Appetite, CareTask, Mood, Movement, Session } from "../types";
import { optionalText } from "./formHelpers";

const emptyReportForm = {
  animal_id: "",
  task_id: "",
  mood: "normal" as Mood,
  appetite: "normal" as Appetite,
  movement: "normal" as Movement,
  visible_injuries: false,
  needs_vet_check: false,
  notes: ""
};

export function KeeperCalendarView({
  session,
  animals,
  careTasks,
  conditionReports,
  reload
}: {
  session: Session;
  animals: Animal[];
  careTasks: CareTask[];
  conditionReports: AnimalConditionReport[];
  reload: () => Promise<void>;
}) {
  const [reportForm, setReportForm] = useState(emptyReportForm);
  const today = new Date().toISOString().slice(0, 10);
  const todayTasks = useMemo(
    () => careTasks.filter((task) => task.due_date === today).sort((a, b) => (a.due_time ?? "").localeCompare(b.due_time ?? "")),
    [careTasks, today]
  );

  const submitReport = async (event: FormEvent) => {
    event.preventDefault();
    await api.createConditionReport(session.csrf_token, {
      animal_id: Number(reportForm.animal_id),
      task_id: reportForm.task_id ? Number(reportForm.task_id) : null,
      mood: reportForm.mood,
      appetite: reportForm.appetite,
      movement: reportForm.movement,
      visible_injuries: reportForm.visible_injuries,
      needs_vet_check: reportForm.needs_vet_check,
      notes: optionalText(reportForm.notes)
    });
    setReportForm(emptyReportForm);
    await reload();
  };

  return (
    <div className="view-stack">
      <Panel title="Heutige Pflege" icon="calendar">
        <div className="status-list">
          {todayTasks.length ? (
            todayTasks.map((task) => (
              <div className="status-row" key={task.id}>
                <strong>{task.title}</strong>
                <small>
                  {task.due_time ? task.due_time.slice(0, 5) : "Ganztags"}
                  {task.animal ? ` - ${task.animal.name}` : ""}
                  {task.enclosure ? ` - ${task.enclosure.name}` : ""}
                </small>
                <StatusChip value={task.status} tone={task.status === "done" ? "ok" : "warning"} />
                {task.status !== "done" ? (
                  <button
                    className="icon-button"
                    title="Aufgabe erledigen"
                    type="button"
                    onClick={async () => {
                      await api.updateCareTask(session.csrf_token, task.id, { status: "done" });
                      await reload();
                    }}
                  >
                    <Icon name="check" />
                  </button>
                ) : null}
              </div>
            ))
          ) : (
            <p className="empty-state">Keine Pflegeaufgaben fuer heute.</p>
          )}
        </div>
      </Panel>

      <Panel title="Zustandsbericht" icon="paw">
        <form className="inline-form condition-form" onSubmit={submitReport}>
          <select value={reportForm.animal_id} onChange={(event) => setReportForm({ ...reportForm, animal_id: event.target.value })} required>
            <option value="">Tier waehlen</option>
            {animals.map((animal) => (
              <option key={animal.id} value={animal.id}>
                {animal.name}
              </option>
            ))}
          </select>
          <select value={reportForm.task_id} onChange={(event) => setReportForm({ ...reportForm, task_id: event.target.value })}>
            <option value="">Ohne Aufgabenbezug</option>
            {todayTasks.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title}
              </option>
            ))}
          </select>
          <select value={reportForm.mood} onChange={(event) => setReportForm({ ...reportForm, mood: event.target.value as Mood })}>
            <option value="normal">Stimmung normal</option>
            <option value="nervous">Nervoes</option>
            <option value="aggressive">Aggressiv</option>
            <option value="tired">Muede</option>
            <option value="playful">Spielerisch</option>
          </select>
          <select value={reportForm.appetite} onChange={(event) => setReportForm({ ...reportForm, appetite: event.target.value as Appetite })}>
            <option value="normal">Fressverhalten normal</option>
            <option value="low">Wenig</option>
            <option value="high">Viel</option>
            <option value="refused">Verweigert</option>
          </select>
          <select value={reportForm.movement} onChange={(event) => setReportForm({ ...reportForm, movement: event.target.value as Movement })}>
            <option value="normal">Bewegung normal</option>
            <option value="limping">Humpelt</option>
            <option value="weak">Schwach</option>
            <option value="hyperactive">Hyperaktiv</option>
          </select>
          <label className="checkbox-row">
            <input
              checked={reportForm.visible_injuries}
              onChange={(event) => setReportForm({ ...reportForm, visible_injuries: event.target.checked })}
              type="checkbox"
            />
            Sichtbare Verletzung
          </label>
          <label className="checkbox-row">
            <input
              checked={reportForm.needs_vet_check}
              onChange={(event) => setReportForm({ ...reportForm, needs_vet_check: event.target.checked })}
              type="checkbox"
            />
            Vet pruefen lassen
          </label>
          <textarea
            value={reportForm.notes}
            onChange={(event) => setReportForm({ ...reportForm, notes: event.target.value })}
            placeholder="Notizen"
            maxLength={5000}
          />
          <button className="primary-button" type="submit">
            <Icon name="plus" />
            Erfassen
          </button>
        </form>
      </Panel>

      <Panel title="Letzte Zustandsberichte" icon="file">
        <div className="timeline">
          {conditionReports.slice(0, 6).map((report) => (
            <article key={report.id}>
              <span>{new Date(report.created_at).toLocaleDateString("de-DE")}</span>
              <strong>{report.animal.name}</strong>
              <p>
                Stimmung {report.mood}, Fressen {report.appetite}, Bewegung {report.movement}
              </p>
              <small>{report.needs_vet_check ? "Vet-Pruefung angefordert" : report.notes ?? "Keine Notiz"}</small>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
