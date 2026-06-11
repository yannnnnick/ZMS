import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { useMutation } from "../hooks/useMutation";
import type { Animal, HealthRecord, RecordType, Session } from "../types";
import { optionalText } from "./formHelpers";

const emptyHealthForm = {
  animal_id: "",
  record_type: "checkup" as RecordType,
  description: "",
  medication: "",
  next_check_date: ""
};

export function HealthView({
  session,
  animals,
  healthRecords,
  reload
}: {
  session: Session;
  animals: Animal[];
  healthRecords: HealthRecord[];
  reload: () => Promise<void>;
}) {
  const [form, setForm] = useState(emptyHealthForm);
  const { isSubmitting, error, run } = useMutation();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const ok = await run(() =>
      api.createHealthRecord(session.csrf_token, {
        ...form,
        animal_id: Number(form.animal_id),
        medication: optionalText(form.medication),
        next_check_date: form.next_check_date || null
      })
    );
    if (!ok) return;
    setForm(emptyHealthForm);
    await reload();
  };

  return (
    <div className="view-stack">
      <Panel title="Gesundheitseintrag" icon="heart">
        <form className="inline-form" onSubmit={submit}>
          <select value={form.animal_id} onChange={(event) => setForm({ ...form, animal_id: event.target.value })} required>
            <option value="">Tier waehlen</option>
            {animals.map((animal) => (
              <option key={animal.id} value={animal.id}>
                {animal.name}
              </option>
            ))}
          </select>
          <select
            value={form.record_type}
            onChange={(event) => setForm({ ...form, record_type: event.target.value as RecordType })}
          >
            <option value="checkup">Checkup</option>
            <option value="medication">Medikation</option>
            <option value="incident">Vorfall</option>
            <option value="note">Notiz</option>
          </select>
          <input
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            placeholder="Beschreibung"
            maxLength={10000}
            required
          />
          <input
            value={form.medication}
            onChange={(event) => setForm({ ...form, medication: event.target.value })}
            placeholder="Medikation"
            maxLength={5000}
          />
          <input
            value={form.next_check_date}
            onChange={(event) => setForm({ ...form, next_check_date: event.target.value })}
            type="date"
            aria-label="Naechste Kontrolle"
          />
          <button className="primary-button" type="submit" disabled={isSubmitting}>
            <Icon name="plus" />
            {isSubmitting ? "Speichere..." : "Erfassen"}
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </form>
      </Panel>
      <Panel title="Gesundheitsverlauf" icon="heart">
        <div className="timeline">
          {healthRecords.map((record) => (
            <article key={record.id}>
              <span>{new Date(record.created_at).toLocaleDateString("de-DE")}</span>
              <strong>{record.animal.name}</strong>
              <p>{record.description}</p>
              <small>
                {record.record_type}
                {record.medication ? ` - ${record.medication}` : ""}
              </small>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
