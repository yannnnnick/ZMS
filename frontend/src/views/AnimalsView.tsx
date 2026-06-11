import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { healthLabels } from "../constants";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import { StatusChip, toneForHealth } from "../components/StatusChip";
import { useMutation } from "../hooks/useMutation";
import type { Animal, Enclosure, HealthStatus, Session, Sex, Species } from "../types";

const emptyAnimalForm = {
  name: "",
  species_id: "",
  enclosure_id: "",
  birth_date: "",
  sex: "unknown" as Sex,
  health_status: "healthy" as HealthStatus
};

export function AnimalsView({
  session,
  animals,
  species,
  enclosures,
  reload
}: {
  session: Session;
  animals: Animal[];
  species: Species[];
  enclosures: Enclosure[];
  reload: () => Promise<void>;
}) {
  const [form, setForm] = useState(emptyAnimalForm);
  const canCreate = ["admin", "keeper"].includes(session.role);
  const canPatchHealth = ["admin", "keeper", "vet"].includes(session.role);
  const { isSubmitting, error, run } = useMutation();
  const rowAction = useMutation();

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const ok = await run(() =>
      api.createAnimal(session.csrf_token, {
        ...form,
        species_id: Number(form.species_id),
        enclosure_id: Number(form.enclosure_id),
        birth_date: form.birth_date || null
      })
    );
    if (!ok) return;
    setForm(emptyAnimalForm);
    await reload();
  };

  return (
    <div className="view-stack">
      {canCreate ? (
        <Panel title="Tier anlegen" icon="paw">
          <form className="inline-form" onSubmit={submit}>
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Name"
              maxLength={120}
              required
            />
            <select
              value={form.species_id}
              onChange={(event) => setForm({ ...form, species_id: event.target.value })}
              required
              aria-label="Art"
            >
              <option value="">Art waehlen</option>
              {species.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.common_name}
                </option>
              ))}
            </select>
            <select
              value={form.enclosure_id}
              onChange={(event) => setForm({ ...form, enclosure_id: event.target.value })}
              required
              aria-label="Gehege"
            >
              <option value="">Gehege waehlen</option>
              {enclosures.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <input
              value={form.birth_date}
              onChange={(event) => setForm({ ...form, birth_date: event.target.value })}
              type="date"
              aria-label="Geburtsdatum"
            />
            <select
              value={form.sex}
              onChange={(event) => setForm({ ...form, sex: event.target.value as Sex })}
              aria-label="Geschlecht"
            >
              <option value="unknown">Unbekannt</option>
              <option value="female">Weiblich</option>
              <option value="male">Maennlich</option>
            </select>
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              <Icon name="plus" />
              {isSubmitting ? "Speichere..." : "Anlegen"}
            </button>
            {error ? <p className="form-error">{error}</p> : null}
          </form>
        </Panel>
      ) : null}

      {rowAction.error ? <p className="form-error">{rowAction.error}</p> : null}

      <Panel title="Tierliste" icon="paw">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Art</th>
                <th>Gehege</th>
                <th>Status</th>
                <th>Aktion</th>
              </tr>
            </thead>
            <tbody>
              {animals.map((animal) => (
                <tr key={animal.id}>
                  <td>
                    <strong>{animal.name}</strong>
                    <small>{animal.age_years != null ? `${animal.age_years} Jahre` : (animal.birth_date ?? animal.sex)}</small>
                  </td>
                  <td>{animal.species.common_name}</td>
                  <td>{animal.enclosure.name}</td>
                  <td>
                    <StatusChip value={healthLabels[animal.health_status]} tone={toneForHealth(animal.health_status)} />
                  </td>
                  <td className="action-cell">
                    {canPatchHealth ? (
                      <select
                        value={animal.health_status}
                        aria-label={`Gesundheitsstatus fuer ${animal.name}`}
                        disabled={rowAction.isSubmitting}
                        onChange={async (event) => {
                          const value = event.target.value;
                          const ok = await rowAction.run(() =>
                            api.updateAnimal(session.csrf_token, animal.id, { health_status: value })
                          );
                          if (ok) await reload();
                        }}
                      >
                        {Object.entries(healthLabels).map(([key, label]) => (
                          <option key={key} value={key}>
                            {label}
                          </option>
                        ))}
                      </select>
                    ) : null}
                    {session.role === "admin" ? (
                      <button
                        className="icon-button danger"
                        title="Archivieren"
                        type="button"
                        disabled={rowAction.isSubmitting}
                        onClick={async () => {
                          const ok = await rowAction.run(() => api.deleteAnimal(session.csrf_token, animal.id));
                          if (ok) await reload();
                        }}
                      >
                        <Icon name="trash" />
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
