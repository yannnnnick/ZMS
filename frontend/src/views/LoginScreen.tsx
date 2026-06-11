import { useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError } from "../api";
import { Icon } from "../components/Icon";
import type { Session } from "../types";

export function LoginScreen({ onLogin }: { onLogin: (session: Session) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              autoComplete="username"
              maxLength={255}
              required
            />
          </label>
          <label>
            Passwort
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              autoComplete="current-password"
              minLength={10}
              maxLength={128}
              required
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" disabled={isLoading} type="submit">
            <Icon name="login" />
            {isLoading ? "Pruefe..." : "Einloggen"}
          </button>
        </form>
      </section>
    </main>
  );
}
