import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { FeedingList } from "../components/Lists";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { useMutation } from "../hooks/useMutation";
import type { Animal, FeedingSchedule, Role, Session } from "../types";
import { optionalText } from "./formHelpers";

const emptyFeedingForm = {
  animal_id: "",
  food_type: "",
  amount: "",
  scheduled_time: "09:00",
  recurrence: "taeglich",
  responsible_role: "keeper" as Role,
  notes: ""
};

export function FeedingsView({
  session,
  animals,
  feedings,
  reload
}: {
  session: Session;
  animals: Animal[];
  feedings: FeedingSchedule[];
  reload: () => Promise<void>;
}) {
  const [form, setForm] = useState(emptyFeedingForm);
  const canCreate = ["admin", "keeper"].includes(session.role);
  const { isSubmitting, error, run } = useMutation();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const ok = await run(() =>
      api.createFeeding(session.csrf_token, {
        ...form,
        animal_id: Number(form.animal_id),
        notes: optionalText(form.notes)
      })
    );
    if (!ok) return;
    setForm(emptyFeedingForm);
    await reload();
  };

  return (
    <div className="view-stack">
      {canCreate ? (
        <Panel title="Fuetterungsplan anlegen" icon="clock">
          <form className="inline-form" onSubmit={submit}>
            <select value={form.animal_id} onChange={(event) => setForm({ ...form, animal_id: event.target.value })} required>
              <option value="">Tier waehlen</option>
              {animals.map((animal) => (
                <option key={animal.id} value={animal.id}>
                  {animal.name}
                </option>
              ))}
            </select>
            <input
              value={form.food_type}
              onChange={(event) => setForm({ ...form, food_type: event.target.value })}
              placeholder="Futter"
              maxLength={120}
              required
            />
            <input
              value={form.amount}
              onChange={(event) => setForm({ ...form, amount: event.target.value })}
              placeholder="Menge"
              maxLength={80}
              required
            />
            <input value={form.scheduled_time} onChange={(event) => setForm({ ...form, scheduled_time: event.target.value })} type="time" required />
            <input
              value={form.recurrence}
              onChange={(event) => setForm({ ...form, recurrence: event.target.value })}
              placeholder="Wiederholung"
              maxLength={80}
              required
            />
            <select
              value={form.responsible_role}
              onChange={(event) => setForm({ ...form, responsible_role: event.target.value as Role })}
              aria-label="Zustaendige Rolle"
            >
              <option value="keeper">Keeper</option>
              <option value="vet">Vet</option>
              <option value="admin">Admin</option>
            </select>
            <textarea
              value={form.notes}
              onChange={(event) => setForm({ ...form, notes: event.target.value })}
              placeholder="Notizen"
              maxLength={5000}
            />
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              <Icon name="plus" />
              {isSubmitting ? "Speichere..." : "Speichern"}
            </button>
            {error ? <p className="form-error">{error}</p> : null}
          </form>
        </Panel>
      ) : null}
      <Panel title="Fuetterungen" icon="clock">
        <FeedingList feedings={feedings} />
      </Panel>
    </div>
  );
}
