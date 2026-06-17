import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { StatusChip } from "../components/StatusChip";
import type { Animal, MedicalReport, Session, VetTask } from "../types";
import { optionalText } from "./formHelpers";

const priorityTone: Record<string, "neutral" | "warning" | "danger"> = {
  low: "neutral",
  medium: "warning",
  high: "danger",
  emergency: "danger"
};

const emptyReportForm = {
  animal_id: "",
  task_id: "",
  diagnosis: "",
  treatment: "",
  medication: "",
  follow_up_required: false,
  follow_up_date: "",
  notes: ""
};

export function VetCalendarView({
  session,
  animals,
  vetTasks,
  medicalReports,
  reload
}: {
  session: Session;
  animals: Animal[];
  vetTasks: VetTask[];
  medicalReports: MedicalReport[];
  reload: () => Promise<void>;
}) {
  const [reportForm, setReportForm] = useState(emptyReportForm);

  const selectTask = (taskId: string) => {
    const task = vetTasks.find((item) => item.id === Number(taskId));
    setReportForm({ ...reportForm, task_id: taskId, animal_id: task ? String(task.animal_id) : reportForm.animal_id });
  };

  const submitReport = async (event: FormEvent) => {
    event.preventDefault();
    await api.createMedicalReport(session.csrf_token, {
      animal_id: Number(reportForm.animal_id),
      task_id: reportForm.task_id ? Number(reportForm.task_id) : null,
      diagnosis: reportForm.diagnosis,
      treatment: optionalText(reportForm.treatment),
      medication: optionalText(reportForm.medication),
      follow_up_required: reportForm.follow_up_required,
      follow_up_date: reportForm.follow_up_date || null,
      notes: optionalText(reportForm.notes)
    });
    setReportForm(emptyReportForm);
    await reload();
  };

  return (
    <div className="view-stack">
      <Panel title="Medizinischer Kalender" icon="heart">
        <div className="status-list">
          {vetTasks.length ? (
            vetTasks.map((task) => (
              <div className="status-row" key={task.id}>
                <strong>{task.title}</strong>
                <small>
                  {new Date(task.due_date).toLocaleDateString("de-DE")} - {task.animal.name}
                </small>
                <StatusChip value={task.priority} tone={priorityTone[task.priority]} />
                <StatusChip value={task.status} tone={task.status === "done" ? "ok" : "warning"} />
                {task.status !== "done" ? (
                  <button
                    className="icon-button"
                    aria-label="Aufgabe abschliessen"
                    title="Aufgabe abschliessen"
                    type="button"
                    onClick={async () => {
                      await api.updateVetTask(session.csrf_token, task.id, { status: "done" });
                      await reload();
                    }}
                  >
                    <Icon name="check" />
                  </button>
                ) : null}
              </div>
            ))
          ) : (
            <p className="empty-state">Keine Vet-Aufgaben.</p>
          )}
        </div>
      </Panel>

      <Panel title="Medizinischen Bericht erfassen" icon="file">
        <form className="inline-form condition-form" onSubmit={submitReport}>
          <select value={reportForm.task_id} onChange={(event) => selectTask(event.target.value)}>
            <option value="">Ohne Aufgabenbezug</option>
            {vetTasks.map((task) => (
              <option key={task.id} value={task.id}>
                {task.title}
              </option>
            ))}
          </select>
          <select value={reportForm.animal_id} onChange={(event) => setReportForm({ ...reportForm, animal_id: event.target.value })} required>
            <option value="">Tier waehlen</option>
            {animals.map((animal) => (
              <option key={animal.id} value={animal.id}>
                {animal.name}
              </option>
            ))}
          </select>
          <input
            value={reportForm.diagnosis}
            onChange={(event) => setReportForm({ ...reportForm, diagnosis: event.target.value })}
            placeholder="Diagnose"
            maxLength={10000}
            required
          />
          <input
            value={reportForm.treatment}
            onChange={(event) => setReportForm({ ...reportForm, treatment: event.target.value })}
            placeholder="Behandlung"
            maxLength={5000}
          />
          <input
            value={reportForm.medication}
            onChange={(event) => setReportForm({ ...reportForm, medication: event.target.value })}
            placeholder="Medikation"
            maxLength={5000}
          />
          <label className="checkbox-row">
            <input
              checked={reportForm.follow_up_required}
              onChange={(event) => setReportForm({ ...reportForm, follow_up_required: event.target.checked })}
              type="checkbox"
            />
            Nachkontrolle
          </label>
          <input
            value={reportForm.follow_up_date}
            onChange={(event) => setReportForm({ ...reportForm, follow_up_date: event.target.value })}
            type="date"
            aria-label="Nachkontroll-Datum"
          />
          <textarea
            value={reportForm.notes}
            onChange={(event) => setReportForm({ ...reportForm, notes: event.target.value })}
            placeholder="Notizen"
            maxLength={5000}
          />
          <button className="primary-button" type="submit">
            <Icon name="plus" />
            Speichern
          </button>
        </form>
      </Panel>

      <Panel title="Letzte medizinische Berichte" icon="heart">
        <div className="timeline">
          {medicalReports.slice(0, 6).map((report) => (
            <article key={report.id}>
              <span>{new Date(report.created_at).toLocaleDateString("de-DE")}</span>
              <strong>{report.animal.name}</strong>
              <p>{report.diagnosis}</p>
              <small>{report.medication ?? report.treatment ?? "Keine Zusatzangaben"}</small>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
