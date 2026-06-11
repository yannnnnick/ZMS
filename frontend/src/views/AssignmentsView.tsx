import { useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import type { Animal, AnimalAssignment, AssignmentRoleType, Enclosure, EnclosureAssignment, Session, User } from "../types";

const emptyAnimalAssignment = {
  animal_id: "",
  user_id: "",
  role_type: "keeper" as AssignmentRoleType
};

const emptyEnclosureAssignment = {
  enclosure_id: "",
  user_id: ""
};

export function AssignmentsView({
  session,
  users,
  animals,
  enclosures,
  animalAssignments,
  enclosureAssignments,
  reload
}: {
  session: Session;
  users: User[];
  animals: Animal[];
  enclosures: Enclosure[];
  animalAssignments: AnimalAssignment[];
  enclosureAssignments: EnclosureAssignment[];
  reload: () => Promise<void>;
}) {
  const [animalForm, setAnimalForm] = useState(emptyAnimalAssignment);
  const [enclosureForm, setEnclosureForm] = useState(emptyEnclosureAssignment);
  const assignableUsers = users.filter((user) => user.role === "keeper" || user.role === "vet");

  const submitAnimalAssignment = async (event: FormEvent) => {
    event.preventDefault();
    await api.createAnimalAssignment(session.csrf_token, {
      animal_id: Number(animalForm.animal_id),
      user_id: Number(animalForm.user_id),
      role_type: animalForm.role_type
    });
    setAnimalForm(emptyAnimalAssignment);
    await reload();
  };

  const submitEnclosureAssignment = async (event: FormEvent) => {
    event.preventDefault();
    await api.createEnclosureAssignment(session.csrf_token, {
      enclosure_id: Number(enclosureForm.enclosure_id),
      user_id: Number(enclosureForm.user_id)
    });
    setEnclosureForm(emptyEnclosureAssignment);
    await reload();
  };

  return (
    <div className="view-stack">
      <section className="split-grid">
        <Panel title="Tier zuweisen" icon="users">
          <form className="inline-form compact-form" onSubmit={submitAnimalAssignment}>
            <select value={animalForm.animal_id} onChange={(event) => setAnimalForm({ ...animalForm, animal_id: event.target.value })} required>
              <option value="">Tier waehlen</option>
              {animals.map((animal) => (
                <option key={animal.id} value={animal.id}>
                  {animal.name}
                </option>
              ))}
            </select>
            <select
              value={animalForm.user_id}
              onChange={(event) => {
                const user = users.find((item) => item.id === Number(event.target.value));
                setAnimalForm({
                  ...animalForm,
                  user_id: event.target.value,
                  role_type: user?.role === "vet" ? "vet" : "keeper"
                });
              }}
              required
            >
              <option value="">Mitarbeiter waehlen</option>
              {assignableUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.display_name} ({user.role})
                </option>
              ))}
            </select>
            <select
              value={animalForm.role_type}
              onChange={(event) => setAnimalForm({ ...animalForm, role_type: event.target.value as AssignmentRoleType })}
            >
              <option value="keeper">Keeper</option>
              <option value="vet">Vet</option>
            </select>
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Zuweisen
            </button>
          </form>
        </Panel>

        <Panel title="Gehege zuweisen" icon="shield">
          <form className="inline-form compact-form" onSubmit={submitEnclosureAssignment}>
            <select
              value={enclosureForm.enclosure_id}
              onChange={(event) => setEnclosureForm({ ...enclosureForm, enclosure_id: event.target.value })}
              required
            >
              <option value="">Gehege waehlen</option>
              {enclosures.map((enclosure) => (
                <option key={enclosure.id} value={enclosure.id}>
                  {enclosure.name}
                </option>
              ))}
            </select>
            <select value={enclosureForm.user_id} onChange={(event) => setEnclosureForm({ ...enclosureForm, user_id: event.target.value })} required>
              <option value="">Mitarbeiter waehlen</option>
              {assignableUsers.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.display_name} ({user.role})
                </option>
              ))}
            </select>
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Zuweisen
            </button>
          </form>
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Aktive Tier-Zuweisungen" icon="paw">
          <div className="status-list">
            {animalAssignments.map((assignment) => (
              <div className="status-row" key={assignment.id}>
                <strong>{assignment.animal.name}</strong>
                <small>
                  {assignment.user.display_name} - {assignment.role_type}
                </small>
                <span>{assignment.animal.enclosure.name}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Aktive Gehege-Zuweisungen" icon="shield">
          <div className="status-list">
            {enclosureAssignments.map((assignment) => (
              <div className="status-row" key={assignment.id}>
                <strong>{assignment.enclosure.name}</strong>
                <small>{assignment.user.display_name}</small>
                <span>{assignment.enclosure.location}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>
    </div>
  );
}
