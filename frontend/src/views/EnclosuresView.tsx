import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { StatusChip, toneForStatus } from "../components/StatusChip";
import { useMutation } from "../hooks/useMutation";
import type { Enclosure, SafetyStatus, Session } from "../types";
import { optionalText } from "./formHelpers";

const emptyEnclosureForm = {
  name: "",
  location: "",
  capacity: "1",
  safety_status: "ok" as SafetyStatus,
  notes: ""
};

export function EnclosuresView({
  session,
  enclosures,
  reload
}: {
  session: Session;
  enclosures: Enclosure[];
  reload: () => Promise<void>;
}) {
  const [form, setForm] = useState(emptyEnclosureForm);
  const isAdmin = session.role === "admin";
  const { isSubmitting, error, run } = useMutation();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const ok = await run(() =>
      api.createEnclosure(session.csrf_token, {
        ...form,
        capacity: Number(form.capacity),
        notes: optionalText(form.notes)
      })
    );
    if (!ok) return;
    setForm(emptyEnclosureForm);
    await reload();
  };

  return (
    <div className="view-stack">
      {isAdmin ? (
        <Panel title="Gehege anlegen" icon="shield">
          <form className="inline-form" onSubmit={submit}>
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Name"
              maxLength={120}
              required
            />
            <input
              value={form.location}
              onChange={(event) => setForm({ ...form, location: event.target.value })}
              placeholder="Standort"
              maxLength={120}
              required
            />
            <input
              value={form.capacity}
              onChange={(event) => setForm({ ...form, capacity: event.target.value })}
              type="number"
              min="1"
              max="10000"
              placeholder="Kapazitaet"
              required
            />
            <select
              value={form.safety_status}
              onChange={(event) => setForm({ ...form, safety_status: event.target.value as SafetyStatus })}
            >
              <option value="ok">OK</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
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
      <Panel title="Gehege" icon="shield">
        <div className="card-list">
          {enclosures.map((item) => (
            <article className="list-card" key={item.id}>
              <strong>{item.name}</strong>
              <span>
                {item.location} - Kapazitaet {item.capacity}
              </span>
              <StatusChip value={item.safety_status} tone={toneForStatus(item.safety_status)} />
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
