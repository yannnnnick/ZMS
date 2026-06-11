import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { StatusChip } from "../components/StatusChip";
import { useMutation } from "../hooks/useMutation";
import type { Session, Species } from "../types";
import { optionalText } from "./formHelpers";

const emptySpeciesForm = {
  common_name: "",
  scientific_name: "",
  category: "Saeugetier",
  conservation_status: "",
  husbandry_notes: ""
};

export function SpeciesView({
  session,
  species,
  reload
}: {
  session: Session;
  species: Species[];
  reload: () => Promise<void>;
}) {
  const [form, setForm] = useState(emptySpeciesForm);
  const isAdmin = session.role === "admin";
  const { isSubmitting, error, run } = useMutation();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const ok = await run(() =>
      api.createSpecies(session.csrf_token, {
        common_name: form.common_name,
        scientific_name: optionalText(form.scientific_name),
        category: form.category,
        conservation_status: optionalText(form.conservation_status),
        husbandry_notes: optionalText(form.husbandry_notes)
      })
    );
    if (!ok) return;
    setForm(emptySpeciesForm);
    await reload();
  };

  return (
    <div className="view-stack">
      {isAdmin ? (
        <Panel title="Art anlegen" icon="leaf">
          <form className="inline-form" onSubmit={submit}>
            <input
              value={form.common_name}
              onChange={(event) => setForm({ ...form, common_name: event.target.value })}
              placeholder="Name der Art"
              maxLength={120}
              required
            />
            <input
              value={form.scientific_name}
              onChange={(event) => setForm({ ...form, scientific_name: event.target.value })}
              placeholder="Wissenschaftlicher Name"
              maxLength={160}
            />
            <input
              value={form.category}
              onChange={(event) => setForm({ ...form, category: event.target.value })}
              placeholder="Kategorie"
              maxLength={80}
              required
            />
            <input
              value={form.conservation_status}
              onChange={(event) => setForm({ ...form, conservation_status: event.target.value })}
              placeholder="Schutzstatus"
              maxLength={120}
            />
            <textarea
              value={form.husbandry_notes}
              onChange={(event) => setForm({ ...form, husbandry_notes: event.target.value })}
              placeholder="Haltungshinweise"
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
      <Panel title="Arten" icon="leaf">
        <div className="card-list">
          {species.map((item) => (
            <article className="list-card" key={item.id}>
              <strong>{item.common_name}</strong>
              <span>{item.scientific_name ?? "Wissenschaftlicher Name offen"}</span>
              <StatusChip value={item.category} tone="neutral" />
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}
