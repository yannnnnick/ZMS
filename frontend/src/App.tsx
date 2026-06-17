import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { csrfCookieName, navItems, roleLabels } from "./constants";
import type { ViewKey } from "./constants";
import { DataWorkspace } from "./components/DataWorkspace";
import { Icon } from "./components/Icon";
import { StatusChip } from "./components/StatusChip";
import type { Session } from "./types";
import { LoginScreen } from "./views/LoginScreen";

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

const roleDefaultViewMap: Record<Session["role"], ViewKey> = {
  viewer: "visitorMap",
  keeper: "keeperCalendar",
  vet: "vetCalendar",
  admin: "dashboard"
};

function defaultViewForRole(role: Session["role"]): ViewKey {
  return roleDefaultViewMap[role] ?? "dashboard";
}

const publicVisitorSession: Session = {
  role: "viewer",
  display_name: "Besucher",
  csrf_token: ""
};

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [view, setView] = useState<ViewKey>("dashboard");
  const [isPublicVisitor, setIsPublicVisitor] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  const clearSession = useCallback(() => {
    setSession(null);
    setIsPublicVisitor(false);
    setView("dashboard");
  }, []);

  useEffect(() => {
    let isActive = true;
    async function restoreSession() {
      try {
        const user = await api.me();
        const csrfToken = readCookie(csrfCookieName);
        if (!csrfToken) throw new Error("Missing CSRF token");
        if (isActive) {
          setSession({ role: user.role, display_name: user.display_name, csrf_token: csrfToken });
          setView(defaultViewForRole(user.role));
        }
      } catch {
        if (isActive) {
          clearSession();
        }
      } finally {
        if (isActive) {
          setIsCheckingSession(false);
        }
      }
    }

    void restoreSession();
    return () => {
      isActive = false;
    };
  }, [clearSession]);

  const handleLogin = useCallback((nextSession: Session) => {
    setSession(nextSession);
    setIsPublicVisitor(false);
    setView(defaultViewForRole(nextSession.role));
  }, []);

  const handleLogout = useCallback(async () => {
    if (!session) {
      clearSession();
      return;
    }
    try {
      await api.logout(session.csrf_token);
    } catch {
      // Local session is cleared even if the server-side logout audit fails.
    } finally {
      clearSession();
    }
  }, [clearSession, session]);

  const effectiveSession = session ?? (isPublicVisitor ? publicVisitorSession : null);
  const availableNav = useMemo(
    () => (effectiveSession ? navItems.filter((item) => !item.roles || item.roles.includes(effectiveSession.role)) : []),
    [effectiveSession]
  );
  const activeView = availableNav.some((item) => item.key === view) ? view : (availableNav[0]?.key ?? "dashboard");

  if (isCheckingSession) {
    return (
      <main className="login-layout">
        <div className="notice">Session wird geprueft...</div>
      </main>
    );
  }

  if (!effectiveSession) {
    return (
      <LoginScreen
        onLogin={handleLogin}
        onOpenPublicMap={() => {
          setIsPublicVisitor(true);
          setView("visitorMap");
        }}
      />
    );
  }

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
            <span>{effectiveSession.display_name}</span>
            <StatusChip value={roleLabels[effectiveSession.role]} tone="neutral" />
            <button className="icon-button" title={session ? "Abmelden" : "Zur Anmeldung"} type="button" onClick={() => void handleLogout()}>
              <Icon name="logout" />
            </button>
          </div>
        </header>

        <DataWorkspace session={effectiveSession} view={activeView} onUnauthorized={clearSession} />
      </main>
    </div>
  );
}
