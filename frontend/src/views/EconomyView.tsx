import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import { Icon } from "../components/Icon";
import { Panel } from "../components/Panel";
import type { Animal, EconomySummary, FeedingOptimization, SalarySimulation, Session, User } from "../types";

const money = (cents: number) => `${(cents / 100).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR`;

const emptySalaryForm = {
  user_id: "",
  start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  end_date: new Date().toISOString().slice(0, 10)
};

export function EconomyView({
  session,
  economy,
  users,
  animals
}: {
  session: Session;
  economy: EconomySummary | null;
  users: User[];
  animals: Animal[];
}) {
  const [salaryForm, setSalaryForm] = useState(emptySalaryForm);
  const [salaryResult, setSalaryResult] = useState<SalarySimulation | null>(null);
  const [optimizerAnimalId, setOptimizerAnimalId] = useState("");
  const [optimizerResult, setOptimizerResult] = useState<FeedingOptimization | null>(null);

  const maxVisitors = useMemo(() => Math.max(1, ...(economy?.visitor_stats.map((item) => item.visitor_count) ?? [1])), [economy]);

  if (!economy) return null;

  const submitSalary = async (event: FormEvent) => {
    event.preventDefault();
    setSalaryResult(
      await api.salarySimulation(session.csrf_token, {
        user_id: Number(salaryForm.user_id),
        start_date: salaryForm.start_date,
        end_date: salaryForm.end_date
      })
    );
  };

  const submitOptimization = async (event: FormEvent) => {
    event.preventDefault();
    setOptimizerResult(await api.feedingOptimization(session.csrf_token, { animal_id: Number(optimizerAnimalId) }));
  };

  return (
    <div className="view-stack">
      <section className="stat-grid economy-grid">
        <article className="stat-card neutral">
          <Icon name="users" />
          <span>Besucher heute</span>
          <strong>{economy.visitors_today}</strong>
        </article>
        <article className="stat-card neutral">
          <Icon name="chart" />
          <span>Besucher Woche</span>
          <strong>{economy.visitors_week}</strong>
        </article>
        <article className="stat-card warning">
          <Icon name="file" />
          <span>Ticketumsatz Woche</span>
          <strong>{money(economy.ticket_revenue_week)}</strong>
        </article>
        <article className="stat-card warning">
          <Icon name="clock" />
          <span>Personalkosten Monat</span>
          <strong>{money(economy.estimated_payroll_month)}</strong>
        </article>
        <article className="stat-card danger">
          <Icon name="heart" />
          <span>Offene Vet-Faelle</span>
          <strong>{economy.open_vet_cases}</strong>
        </article>
      </section>

      <section className="split-grid">
        <Panel title="Besucherzahlen" icon="chart">
          <div className="bar-chart">
            {economy.visitor_stats.map((item) => (
              <div className="bar-row" key={item.date}>
                <span>{new Date(item.date).toLocaleDateString("de-DE", { weekday: "short" })}</span>
                <div>
                  <i style={{ width: `${(item.visitor_count / maxVisitors) * 100}%` }} />
                </div>
                <strong>{item.visitor_count}</strong>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Lohnsimulation" icon="users">
          <form className="inline-form compact-form" onSubmit={submitSalary}>
            <select value={salaryForm.user_id} onChange={(event) => setSalaryForm({ ...salaryForm, user_id: event.target.value })} required>
              <option value="">Mitarbeiter waehlen</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.display_name}
                </option>
              ))}
            </select>
            <input
              value={salaryForm.start_date}
              onChange={(event) => setSalaryForm({ ...salaryForm, start_date: event.target.value })}
              type="date"
              aria-label="Startdatum"
              required
            />
            <input value={salaryForm.end_date} onChange={(event) => setSalaryForm({ ...salaryForm, end_date: event.target.value })} type="date" aria-label="Enddatum" required />
            <button className="primary-button" type="submit">
              Berechnen
            </button>
          </form>
          {salaryResult ? (
            <div className="result-box">
              <strong>{salaryResult.user.display_name}</strong>
              <span>{salaryResult.hours} Stunden</span>
              <span>Brutto {money(salaryResult.gross_pay)}</span>
              <span>Netto geschaetzt {money(salaryResult.estimated_net)}</span>
              <small>Vereinfachte Simulation</small>
            </div>
          ) : null}
        </Panel>
      </section>

      <Panel title="Futterkosten-Optimierung" icon="leaf">
        <form className="inline-form compact-form" onSubmit={submitOptimization}>
          <select value={optimizerAnimalId} onChange={(event) => setOptimizerAnimalId(event.target.value)} required>
            <option value="">Tier waehlen</option>
            {animals.map((animal) => (
              <option key={animal.id} value={animal.id}>
                {animal.name} - {animal.species.common_name}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit">
            Optimieren
          </button>
        </form>
        {optimizerResult ? (
          <div className="optimizer-result">
            <strong>{optimizerResult.message}</strong>
            <span>Methode: {optimizerResult.method}</span>
            <span>Gesamtkosten: {money(optimizerResult.total_cost)}</span>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Futter</th>
                    <th>Menge</th>
                    <th>Kosten</th>
                  </tr>
                </thead>
                <tbody>
                  {optimizerResult.feeding_plan.map((item) => (
                    <tr key={item.food_item_id}>
                      <td>{item.food_name}</td>
                      <td>
                        {item.quantity} {item.unit}
                      </td>
                      <td>{money(item.cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
