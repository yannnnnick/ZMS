import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api, ApiError } from "./api";
import type {
  Animal,
  AuditLog,
  DashboardSummary,
  Enclosure,
  FeedingSchedule,
  HealthRecord,
  HealthStatus,
  Role,
  Session,
  Species,
  TaskStatus,
  ZooTask
} from "./types";

type ViewKey = "dashboard" | "animals" | "species" | "enclosures" | "feedings" | "health" | "tasks" | "audit";

const STORAGE_KEY = "zoo-management-session-v1";

const roleLabels: Record<Role, string> = {
  admin: "Admin",
  keeper: "Keeper",
  vet: "Vet",
  viewer: "Viewer"
};

const healthLabels: Record<HealthStatus, string> = {
  healthy: "Gesund",
  observation: "Beobachtung",
  treatment: "Behandlung",
  critical: "Kritisch"
};

const navItems: Array<{ key: ViewKey; label: string; icon: IconName; roles?: Role[] }> = [
  { key: "dashboard", label: "Dashboard", icon: "grid" },
  { key: "animals", label: "Tiere", icon: "paw" },
  { key: "species", label: "Arten", icon: "leaf" },
  { key: "enclosures", label: "Gehege", icon: "shield" },
  { key: "feedings", label: "Fuetterungsplaene", icon: "clock", roles: ["admin", "keeper", "vet"] },
  { key: "health", label: "Gesundheit", icon: "heart", roles: ["admin", "vet"] },
  { key: "tasks", label: "Aufgaben", icon: "check" },
  { key: "audit", label: "Audit", icon: "file", roles: ["admin"] }
];

function loadStoredSession(): Session | null {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Session;
    if (parsed.access_token && parsed.role && parsed.display_name) return parsed;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  return null;
}

export default function App() {
  const [session, setSession] = useState<Session | null>(() => loadStoredSession());
  const [view, setView] = useState<ViewKey>("dashboard");

  const handleSession = (nextSession: Session | null) => {
    setSession(nextSession);
    if (nextSession) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  };

  if (!session) {
    return <LoginScreen onLogin={handleSession} />;
  }

  const availableNav = navItems.filter((item) => !item.roles || item.roles.includes(session.role));
  const activeView = availableNav.some((item) => item.key === view) ? view : "dashboard";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">ZM</span>
          <div>
            <strong>Zoo Management</strong>
            <span>Uni-MVP</span>
          </div>
        </div>
        <nav aria-label="Hauptnavigation">
          {availableNav.map((item) => (
            <button
              className={activeView === item.key ? "nav-item active" : "nav-item"}
              key={item.key}
              onClick={() => setView(item.key)}
              type="button"
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{availableNav.find((item) => item.key === activeView)?.label ?? "Dashboard"}</h1>
            <p>Rollenbasierte Verwaltung mit synthetischen Demo-Daten</p>
          </div>
          <div className="userbox">
            <span>{session.display_name}</span>
            <StatusChip value={roleLabels[session.role]} tone="neutral" />
            <button
              className="icon-button"
              title="Abmelden"
              type="button"
              onClick={() => {
                api.logout(session.access_token).catch(() => undefined);
                handleSession(null);
              }}
            >
              <Icon name="logout" />
            </button>
          </div>
        </header>

        <DataWorkspace session={session} view={activeView} />
      </main>
    </div>
  );
}

function LoginScreen({ onLogin }: { onLogin: (session: Session) => void }) {
  const [email, setEmail] = useState("admin@example.test");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const demoAccounts = [
    ["Admin", "admin@example.test", "Admin123!"],
    ["Keeper", "keeper@example.test", "Keeper123!"],
    ["Vet", "vet@example.test", "Vet123!"],
    ["Viewer", "viewer@example.test", "Viewer123!"]
  ] as const;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      onLogin(await api.login(email, password));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login fehlgeschlagen");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="login-layout">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="brand login-brand">
          <span className="brand-mark">ZM</span>
          <div>
            <strong>Zoo Management</strong>
            <span>FastAPI + React MVP</span>
          </div>
        </div>
        <form onSubmit={submit} className="form-stack">
          <div>
            <h1 id="login-title">Anmelden</h1>
            <p>Geschuetzter Zugriff fuer Admin, Keeper, Vet und Viewer.</p>
          </div>
          <label>
            E-Mail
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" autoComplete="username" />
          </label>
          <label>
            Passwort
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" disabled={isLoading} type="submit">
            <Icon name="login" />
            {isLoading ? "Pruefe..." : "Einloggen"}
          </button>
        </form>
        <div className="demo-grid" aria-label="Demo-Zugaenge">
          {demoAccounts.map(([label, accountEmail, accountPassword]) => (
            <button
              key={label}
              type="button"
              onClick={() => {
                setEmail(accountEmail);
                setPassword(accountPassword);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

function DataWorkspace({ session, view }: { session: Session; view: ViewKey }) {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [animals, setAnimals] = useState<Animal[]>([]);
  const [species, setSpecies] = useState<Species[]>([]);
  const [enclosures, setEnclosures] = useState<Enclosure[]>([]);
  const [feedings, setFeedings] = useState<FeedingSchedule[]>([]);
  const [healthRecords, setHealthRecords] = useState<HealthRecord[]>([]);
  const [tasks, setTasks] = useState<ZooTask[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const token = session.access_token;

  const loadData = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      const [dashboardData, animalData, speciesData, enclosureData, taskData] = await Promise.all([
        api.dashboard(token),
        api.animals(token),
        api.species(token),
        api.enclosures(token),
        api.tasks(token)
      ]);
      setDashboard(dashboardData);
      setAnimals(animalData);
      setSpecies(speciesData);
      setEnclosures(enclosureData);
      setTasks(taskData);

      if (["feedings", "dashboard"].includes(view) && session.role !== "viewer") {
        setFeedings(await api.feedings(token));
      }
      if (["health", "dashboard"].includes(view) && ["admin", "vet"].includes(session.role)) {
        setHealthRecords(await api.healthRecords(token));
      }
      if (view === "audit" && session.role === "admin") {
        setAuditLogs(await api.auditLogs(token));
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Backend nicht erreichbar");
    } finally {
      setIsLoading(false);
    }
  }, [session.role, token, view]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const context = {
    session,
    dashboard,
    animals,
    species,
    enclosures,
    feedings,
    healthRecords,
    tasks,
    auditLogs,
    reload: loadData
  };

  return (
    <section className="content-region" aria-busy={isLoading}>
      {error ? (
        <div className="notice error">
          <Icon name="alert" />
          <span>{error}</span>
          <button type="button" onClick={() => void loadData()}>
            Erneut laden
          </button>
        </div>
      ) : null}
      {isLoading ? <div className="notice">Daten werden geladen...</div> : null}
      {!isLoading && view === "dashboard" ? <DashboardView {...context} /> : null}
      {!isLoading && view === "animals" ? <AnimalsView {...context} /> : null}
      {!isLoading && view === "species" ? <SpeciesView {...context} /> : null}
      {!isLoading && view === "enclosures" ? <EnclosuresView {...context} /> : null}
      {!isLoading && view === "feedings" ? <FeedingsView {...context} /> : null}
      {!isLoading && view === "health" ? <HealthView {...context} /> : null}
      {!isLoading && view === "tasks" ? <TasksView {...context} /> : null}
      {!isLoading && view === "audit" ? <AuditView {...context} /> : null}
    </section>
  );
}

interface ViewContext {
  session: Session;
  dashboard: DashboardSummary | null;
  animals: Animal[];
  species: Species[];
  enclosures: Enclosure[];
  feedings: FeedingSchedule[];
  healthRecords: HealthRecord[];
  tasks: ZooTask[];
  auditLogs: AuditLog[];
  reload: () => Promise<void>;
}

function DashboardView({ dashboard, feedings, tasks }: ViewContext) {
  if (!dashboard) return null;
  const stats = [
    ["Tiere", dashboard.animals_total, "paw", "neutral"],
    ["Offene Aufgaben", dashboard.open_tasks, "check", "warning"],
    ["Faellige Fuetterungen", dashboard.due_feedings, "clock", "neutral"],
    ["Kritische Gesundheit", dashboard.critical_health, "heart", "danger"],
    ["Gehege-Warnungen", dashboard.warning_enclosures, "shield", "warning"]
  ] as const;

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
          <TaskList tasks={tasks.slice(0, 5)} />
        </Panel>
      </section>

      <section className="split-grid">
        <Panel title="Fuetterungsplan" icon="clock">
          <FeedingList feedings={feedings.slice(0, 6)} />
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

function AnimalsView({ session, animals, species, enclosures, reload }: ViewContext) {
  const [form, setForm] = useState({
    name: "",
    species_id: "",
    enclosure_id: "",
    sex: "unknown",
    health_status: "healthy"
  });
  const canCreate = ["admin", "keeper"].includes(session.role);
  const canPatchHealth = ["admin", "keeper", "vet"].includes(session.role);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await api.createAnimal(session.access_token, {
      ...form,
      species_id: Number(form.species_id),
      enclosure_id: Number(form.enclosure_id)
    });
    setForm({ name: "", species_id: "", enclosure_id: "", sex: "unknown", health_status: "healthy" });
    await reload();
  };

  return (
    <div className="view-stack">
      {canCreate ? (
        <Panel title="Tier anlegen" icon="paw">
          <form className="inline-form" onSubmit={submit}>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Name" required />
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
            <select value={form.sex} onChange={(event) => setForm({ ...form, sex: event.target.value })} aria-label="Geschlecht">
              <option value="unknown">Unbekannt</option>
              <option value="female">Weiblich</option>
              <option value="male">Maennlich</option>
            </select>
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Anlegen
            </button>
          </form>
        </Panel>
      ) : null}

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
                    <small>{animal.sex}</small>
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
                        onChange={async (event) => {
                          await api.updateAnimal(session.access_token, animal.id, { health_status: event.target.value });
                          await reload();
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
                        onClick={async () => {
                          await api.deleteAnimal(session.access_token, animal.id);
                          await reload();
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

function SpeciesView({ session, species, reload }: ViewContext) {
  const [commonName, setCommonName] = useState("");
  const [category, setCategory] = useState("Saeugetier");
  const isAdmin = session.role === "admin";

  return (
    <div className="view-stack">
      {isAdmin ? (
        <Panel title="Art anlegen" icon="leaf">
          <form
            className="inline-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await api.createSpecies(session.access_token, { common_name: commonName, category });
              setCommonName("");
              await reload();
            }}
          >
            <input value={commonName} onChange={(event) => setCommonName(event.target.value)} placeholder="Name der Art" required />
            <input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Kategorie" required />
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Speichern
            </button>
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

function EnclosuresView({ session, enclosures, reload }: ViewContext) {
  const [form, setForm] = useState({ name: "", location: "", capacity: "1", safety_status: "ok" });
  const isAdmin = session.role === "admin";

  return (
    <div className="view-stack">
      {isAdmin ? (
        <Panel title="Gehege anlegen" icon="shield">
          <form
            className="inline-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await api.createEnclosure(session.access_token, { ...form, capacity: Number(form.capacity) });
              setForm({ name: "", location: "", capacity: "1", safety_status: "ok" });
              await reload();
            }}
          >
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Name" required />
            <input
              value={form.location}
              onChange={(event) => setForm({ ...form, location: event.target.value })}
              placeholder="Standort"
              required
            />
            <input
              value={form.capacity}
              onChange={(event) => setForm({ ...form, capacity: event.target.value })}
              type="number"
              min="1"
              placeholder="Kapazitaet"
              required
            />
            <select value={form.safety_status} onChange={(event) => setForm({ ...form, safety_status: event.target.value })}>
              <option value="ok">OK</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </select>
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Speichern
            </button>
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

function FeedingsView({ session, animals, feedings, reload }: ViewContext) {
  const [form, setForm] = useState({ animal_id: "", food_type: "", amount: "", scheduled_time: "09:00", recurrence: "taeglich" });
  const canCreate = ["admin", "keeper"].includes(session.role);

  return (
    <div className="view-stack">
      {canCreate ? (
        <Panel title="Fuetterungsplan anlegen" icon="clock">
          <form
            className="inline-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await api.createFeeding(session.access_token, {
                ...form,
                animal_id: Number(form.animal_id),
                responsible_role: "keeper"
              });
              setForm({ animal_id: "", food_type: "", amount: "", scheduled_time: "09:00", recurrence: "taeglich" });
              await reload();
            }}
          >
            <select value={form.animal_id} onChange={(event) => setForm({ ...form, animal_id: event.target.value })} required>
              <option value="">Tier waehlen</option>
              {animals.map((animal) => (
                <option key={animal.id} value={animal.id}>
                  {animal.name}
                </option>
              ))}
            </select>
            <input value={form.food_type} onChange={(event) => setForm({ ...form, food_type: event.target.value })} placeholder="Futter" required />
            <input value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} placeholder="Menge" required />
            <input value={form.scheduled_time} onChange={(event) => setForm({ ...form, scheduled_time: event.target.value })} type="time" required />
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Speichern
            </button>
          </form>
        </Panel>
      ) : null}
      <Panel title="Fuetterungen" icon="clock">
        <FeedingList feedings={feedings} />
      </Panel>
    </div>
  );
}

function HealthView({ session, animals, healthRecords, reload }: ViewContext) {
  const [form, setForm] = useState({ animal_id: "", record_type: "checkup", description: "", next_check_date: "" });

  return (
    <div className="view-stack">
      <Panel title="Gesundheitseintrag" icon="heart">
        <form
          className="inline-form"
          onSubmit={async (event) => {
            event.preventDefault();
            await api.createHealthRecord(session.access_token, {
              ...form,
              animal_id: Number(form.animal_id),
              next_check_date: form.next_check_date || null
            });
            setForm({ animal_id: "", record_type: "checkup", description: "", next_check_date: "" });
            await reload();
          }}
        >
          <select value={form.animal_id} onChange={(event) => setForm({ ...form, animal_id: event.target.value })} required>
            <option value="">Tier waehlen</option>
            {animals.map((animal) => (
              <option key={animal.id} value={animal.id}>
                {animal.name}
              </option>
            ))}
          </select>
          <select value={form.record_type} onChange={(event) => setForm({ ...form, record_type: event.target.value })}>
            <option value="checkup">Checkup</option>
            <option value="medication">Medikation</option>
            <option value="incident">Vorfall</option>
            <option value="note">Notiz</option>
          </select>
          <input
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            placeholder="Beschreibung"
            required
          />
          <input
            value={form.next_check_date}
            onChange={(event) => setForm({ ...form, next_check_date: event.target.value })}
            type="date"
            aria-label="Naechste Kontrolle"
          />
          <button className="primary-button" type="submit">
            <Icon name="plus" />
            Erfassen
          </button>
        </form>
      </Panel>
      <Panel title="Gesundheitsverlauf" icon="heart">
        <div className="timeline">
          {healthRecords.map((record) => (
            <article key={record.id}>
              <span>{new Date(record.created_at).toLocaleDateString("de-DE")}</span>
              <strong>{record.animal.name}</strong>
              <p>{record.description}</p>
              <small>{record.record_type}</small>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function TasksView({ session, tasks, reload }: ViewContext) {
  const [form, setForm] = useState({ title: "", task_type: "feeding", assigned_role: "keeper", due_at: "" });
  const canEdit = ["admin", "keeper", "vet"].includes(session.role);

  const defaultDueAt = useMemo(() => {
    const next = new Date(Date.now() + 60 * 60 * 1000);
    next.setMinutes(0, 0, 0);
    return next.toISOString().slice(0, 16);
  }, []);

  useEffect(() => {
    if (!form.due_at) setForm((current) => ({ ...current, due_at: defaultDueAt }));
  }, [defaultDueAt, form.due_at]);

  return (
    <div className="view-stack">
      {canEdit ? (
        <Panel title="Aufgabe anlegen" icon="check">
          <form
            className="inline-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await api.createTask(session.access_token, {
                ...form,
                due_at: new Date(form.due_at).toISOString(),
                status: "open"
              });
              setForm({ title: "", task_type: "feeding", assigned_role: "keeper", due_at: defaultDueAt });
              await reload();
            }}
          >
            <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Titel" required />
            <select value={form.task_type} onChange={(event) => setForm({ ...form, task_type: event.target.value })}>
              <option value="feeding">Fuetterung</option>
              <option value="cleaning">Reinigung</option>
              <option value="checkup">Kontrolle</option>
              <option value="maintenance">Wartung</option>
            </select>
            <select value={form.assigned_role} onChange={(event) => setForm({ ...form, assigned_role: event.target.value })}>
              <option value="keeper">Keeper</option>
              <option value="vet">Vet</option>
              <option value="admin">Admin</option>
            </select>
            <input value={form.due_at} onChange={(event) => setForm({ ...form, due_at: event.target.value })} type="datetime-local" required />
            <button className="primary-button" type="submit">
              <Icon name="plus" />
              Anlegen
            </button>
          </form>
        </Panel>
      ) : null}
      <Panel title="Aufgaben" icon="check">
        <TaskList tasks={tasks} token={session.access_token} canEdit={canEdit} reload={reload} />
      </Panel>
    </div>
  );
}

function AuditView({ auditLogs }: ViewContext) {
  return (
    <Panel title="Audit-Logs" icon="file">
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Zeitpunkt</th>
              <th>Aktion</th>
              <th>Entitaet</th>
              <th>Nutzer-ID</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.timestamp).toLocaleString("de-DE")}</td>
                <td>{entry.action}</td>
                <td>
                  {entry.entity_type} #{entry.entity_id ?? "-"}
                </td>
                <td>{entry.actor_user_id ?? "-"}</td>
                <td>
                  <code>{entry.details ? JSON.stringify(entry.details) : "{}"}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function Panel({ title, icon, children }: { title: string; icon: IconName; children: ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <Icon name={icon} />
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function CompactAnimalTable({ animals }: { animals: Animal[] }) {
  if (!animals.length) return <p className="empty-state">Keine Warnungen.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Tier</th>
            <th>Art</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {animals.map((animal) => (
            <tr key={animal.id}>
              <td>{animal.name}</td>
              <td>{animal.species.common_name}</td>
              <td>
                <StatusChip value={healthLabels[animal.health_status]} tone={toneForHealth(animal.health_status)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TaskList({
  tasks,
  token,
  canEdit = false,
  reload
}: {
  tasks: ZooTask[];
  token?: string;
  canEdit?: boolean;
  reload?: () => Promise<void>;
}) {
  if (!tasks.length) return <p className="empty-state">Keine Aufgaben.</p>;
  return (
    <div className="status-list">
      {tasks.map((task) => (
        <div className="status-row" key={task.id}>
          <span>{task.title}</span>
          <small>{new Date(task.due_at).toLocaleString("de-DE")}</small>
          <StatusChip value={task.status} tone={toneForTask(task.status)} />
          {canEdit && token && reload && task.status !== "done" ? (
            <button
              className="icon-button"
              title="Erledigen"
              type="button"
              onClick={async () => {
                await api.updateTask(token, task.id, { status: "done" });
                await reload();
              }}
            >
              <Icon name="check" />
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function FeedingList({ feedings }: { feedings: FeedingSchedule[] }) {
  if (!feedings.length) return <p className="empty-state">Keine Fuetterungen geladen.</p>;
  return (
    <div className="status-list">
      {feedings.map((feeding) => (
        <div className="status-row" key={feeding.id}>
          <span>{feeding.animal.name}</span>
          <small>
            {feeding.scheduled_time.slice(0, 5)} - {feeding.food_type} - {feeding.amount}
          </small>
          <StatusChip value={feeding.recurrence} tone="neutral" />
        </div>
      ))}
    </div>
  );
}

function StatusChip({ value, tone }: { value: string; tone: "neutral" | "ok" | "warning" | "danger" }) {
  return <span className={`status-chip ${tone}`}>{value}</span>;
}

function toneForHealth(status: HealthStatus): "neutral" | "ok" | "warning" | "danger" {
  if (status === "healthy") return "ok";
  if (status === "critical") return "danger";
  return "warning";
}

function toneForStatus(status: string): "neutral" | "ok" | "warning" | "danger" {
  if (status === "ok") return "ok";
  if (status === "critical") return "danger";
  if (status === "warning") return "warning";
  return "neutral";
}

function toneForTask(status: TaskStatus): "neutral" | "ok" | "warning" | "danger" {
  if (status === "done") return "ok";
  if (status === "in_progress") return "neutral";
  return "warning";
}

type IconName = "grid" | "paw" | "leaf" | "shield" | "clock" | "heart" | "check" | "file" | "logout" | "login" | "plus" | "alert" | "trash";

function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    grid: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
    paw: <path d="M8 9c1.2 0 2-1.1 2-2.5S9.2 4 8 4 6 5.1 6 6.5 6.8 9 8 9Zm8 0c1.2 0 2-1.1 2-2.5S17.2 4 16 4s-2 1.1-2 2.5.8 2.5 2 2.5ZM5 14c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2Zm14 0c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2Zm-7 1c-2.9 0-5 1.7-5 4 0 1.6 1.1 2 2.5 2 .9 0 1.5-.4 2.5-.4s1.6.4 2.5.4c1.4 0 2.5-.4 2.5-2 0-2.3-2.1-4-5-4Z" />,
    leaf: <path d="M20 4c-7.2.2-12 3.9-12 9.7 0 2.1 1.1 3.9 2.8 5C12.4 14.4 15 10.8 19 8c-3 3.4-5.2 7-6.4 11.3C17.2 18.5 21 13.4 20 4ZM4 20c1.7-.6 3.1-1.3 4.4-2.3" />,
    shield: <path d="M12 3 20 6v6c0 5-3.4 8.2-8 9-4.6-.8-8-4-8-9V6l8-3Zm0 4v10" />,
    clock: <path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm0 4v5l3 2" />,
    heart: <path d="M12 21s-8-4.7-8-11a4.5 4.5 0 0 1 8-2.8A4.5 4.5 0 0 1 20 10c0 6.3-8 11-8 11Z" />,
    check: <path d="m5 12 4 4L19 6" />,
    file: <path d="M6 3h8l4 4v14H6zM14 3v5h4M8 13h8M8 17h6" />,
    logout: <path d="M10 17v2H5V5h5v2M14 8l4 4-4 4M18 12H9" />,
    login: <path d="M14 7V5h5v14h-5v-2M10 8l4 4-4 4M14 12H5" />,
    plus: <path d="M12 5v14M5 12h14" />,
    alert: <path d="M12 3 22 20H2L12 3Zm0 6v5m0 3h.01" />,
    trash: <path d="M4 7h16M9 7V5h6v2m-8 3 1 10h8l1-10" />
  };

  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {paths[name]}
    </svg>
  );
}
