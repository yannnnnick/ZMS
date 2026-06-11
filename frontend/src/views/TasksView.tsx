import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { TaskList } from "../components/Lists";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { useMutation } from "../hooks/useMutation";
import type { Animal, Enclosure, Role, Session, TaskType, ZooTask } from "../types";
import { optionalText } from "./formHelpers";

const emptyTaskForm = {
  title: "",
  description: "",
  task_type: "feeding" as TaskType,
  assigned_role: "keeper" as Role,
  due_at: "",
  related_animal_id: "",
  related_enclosure_id: ""
};

export function TasksView({
  session,
  tasks,
  animals,
  enclosures,
  reload
}: {
  session: Session;
  tasks: ZooTask[];
  animals: Animal[];
  enclosures: Enclosure[];
  reload: () => Promise<void>;
}) {
  const [form, setForm] = useState(emptyTaskForm);
  const canEdit = ["admin", "keeper", "vet"].includes(session.role);
  const { isSubmitting, error, run } = useMutation();

  const defaultDueAt = useMemo(() => {
    const next = new Date(Date.now() + 60 * 60 * 1000);
    next.setMinutes(0, 0, 0);
    return next.toISOString().slice(0, 16);
  }, []);

  useEffect(() => {
    if (!form.due_at) setForm((current) => ({ ...current, due_at: defaultDueAt }));
  }, [defaultDueAt, form.due_at]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const ok = await run(() =>
      api.createTask(session.csrf_token, {
        title: form.title,
        description: optionalText(form.description),
        task_type: form.task_type,
        assigned_role: form.assigned_role,
        due_at: new Date(form.due_at).toISOString(),
        related_animal_id: form.related_animal_id ? Number(form.related_animal_id) : null,
        related_enclosure_id: form.related_enclosure_id ? Number(form.related_enclosure_id) : null
      })
    );
    if (!ok) return;
    setForm({ ...emptyTaskForm, due_at: defaultDueAt });
    await reload();
  };

  return (
    <div className="view-stack">
      {canEdit ? (
        <Panel title="Aufgabe anlegen" icon="check">
          <form className="inline-form" onSubmit={submit}>
            <input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="Titel"
              maxLength={160}
              required
            />
            <textarea
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="Beschreibung"
              maxLength={5000}
            />
            <select value={form.task_type} onChange={(event) => setForm({ ...form, task_type: event.target.value as TaskType })}>
              <option value="feeding">Fuetterung</option>
              <option value="cleaning">Reinigung</option>
              <option value="checkup">Kontrolle</option>
              <option value="maintenance">Wartung</option>
            </select>
            <select value={form.assigned_role} onChange={(event) => setForm({ ...form, assigned_role: event.target.value as Role })}>
              <option value="keeper">Keeper</option>
              <option value="vet">Vet</option>
              <option value="admin">Admin</option>
            </select>
            <select
              value={form.related_animal_id}
              onChange={(event) => setForm({ ...form, related_animal_id: event.target.value })}
              aria-label="Verknuepftes Tier"
            >
              <option value="">Kein Tierbezug</option>
              {animals.map((animal) => (
                <option key={animal.id} value={animal.id}>
                  {animal.name}
                </option>
              ))}
            </select>
            <select
              value={form.related_enclosure_id}
              onChange={(event) => setForm({ ...form, related_enclosure_id: event.target.value })}
              aria-label="Verknuepftes Gehege"
            >
              <option value="">Kein Gehegebezug</option>
              {enclosures.map((enclosure) => (
                <option key={enclosure.id} value={enclosure.id}>
                  {enclosure.name}
                </option>
              ))}
            </select>
            <input value={form.due_at} onChange={(event) => setForm({ ...form, due_at: event.target.value })} type="datetime-local" required />
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              <Icon name="plus" />
              {isSubmitting ? "Speichere..." : "Anlegen"}
            </button>
            {error ? <p className="form-error">{error}</p> : null}
          </form>
        </Panel>
      ) : null}
      <Panel title="Aufgaben" icon="check">
        <TaskList tasks={tasks} csrfToken={session.csrf_token} canEdit={canEdit} reload={reload} />
      </Panel>
    </div>
  );
}
