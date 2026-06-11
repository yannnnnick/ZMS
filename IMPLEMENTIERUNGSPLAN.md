# Zoo Management System — Zielstand-Analyse & Implementierungsplan

> **Dokument erstellt:** 2026-06-11  
> **Scope:** Analyse des aktuellen Stands, Identifikation von Schwächen/Fehlern, detaillierter Plan für den Zielstand (6 Phasen)  
> **Vorgehen:** Kein Code wird geschrieben — nur Dokumentation, Architekturplan und Implementierungsanweisungen

---

## 1. Executive Summary

Das aktuelle Zoo-Management-System ist ein solider **MVP** (FastAPI + React) mit:
- JWT-Cookie-Auth + CSRF-Schutz
- Rollen-basiertem Zugriff (admin, keeper, vet, viewer)
- Audit-Logging
- Grundlegenden CRUD-Operationen für Tiere, Gehege, Arten, Fütterungspläne, Gesundheitsakten, Aufgaben

**Das System fehlt jedoch komplett an:**
- Rollen-spezifischen Dashboards/Oberflächen (alle sehen das gleiche)
- Mitarbeiter-Zuweisungen (Keeper/Vet → Tiere/Gehege)
- Pflegekalender mit tagesbasierter Aufgabenansicht
- Zustandsberichten (Stimmung, Fressverhalten, Bewegung)
- Medizinischem Kalender für Tierärzte
- Besucher-Map (interaktive Zoo-Karte)
- Wirtschaftsdashboard (Besucherzahlen, Kosten, Lohnabrechnung)
- Futterkosten-Optimierung (lineare Programmierung)

---

## 2. Aktueller Stand — Detaillierte Analyse

### 2.1 Architektur-Stack

| Layer | Technologie | Status |
|-------|-------------|--------|
| Backend | FastAPI 0.136 + SQLAlchemy 2.0 | ✅ Solide |
| DB | SQLite (dev) / PostgreSQL-ready | ✅ Mit Alembic-Migrationen |
| Auth | JWT (HttpOnly Cookie) + CSRF + Argon2 | ✅ Stark |
| Frontend | React 19 + Vite + TypeScript (strict) | ✅ Solide |
| Styling | Custom CSS (kein Framework) | ✅ Gut wartbar |
| Tests | pytest + TestClient | ✅ 20+ Tests vorhanden |

### 2.2 Vorhandene Datenbank-Tabellen

```
users              → id, email, display_name, password_hash, role, is_active
species            → id, common_name, scientific_name, category, conservation_status, husbandry_notes
enclosures         → id, name, location, capacity, safety_status, notes
animals            → id, name, species_id, enclosure_id, birth_date, sex, health_status, active
feeding_schedules  → id, animal_id, food_type, amount, scheduled_time, recurrence, responsible_role, notes
health_records     → id, animal_id, created_by_user_id, record_type, description, medication, next_check_date
tasks              → id, title, description, task_type, assigned_role, due_at, status, related_animal_id, related_enclosure_id
audit_logs         → id, actor_user_id, action, entity_type, entity_id, timestamp, ip_hash, details
```

### 2.3 Vorhandene API-Endpunkte

| Methode | Endpoint | Rollen | Beschreibung |
|---------|----------|--------|--------------|
| POST | /auth/login | Öffentlich | Login + Cookie-Set |
| POST | /auth/logout | Authentifiziert | Logout + Token-Revoke |
| GET | /me | Authentifiziert | Aktueller User |
| GET | /dashboard | Authentifiziert | Statistiken (alle gleich) |
| GET/POST | /animals | Admin/Keeper (POST), Alle (GET) | Tier-CRUD |
| PATCH | /animals/{id} | Admin/Keeper/Vet (Vet nur health_status) | Tier-Update |
| DELETE | /animals/{id} | Admin | Soft-Delete |
| GET/POST | /species | Admin (POST), Alle (GET) | Arten-CRUD |
| GET/POST | /enclosures | Admin (POST), Alle (GET) | Gehege-CRUD |
| GET/POST | /feeding-schedules | Admin/Keeper/Vet | Fütterungspläne |
| GET/POST | /health-records | Admin/Vet | Gesundheitsakten |
| GET/POST | /tasks | Admin/Keeper/Vet | Aufgaben |
| PATCH/DELETE | /tasks/{id} | Admin/Keeper/Vet | Aufgaben-Update/Delete |
| GET | /audit-logs | Admin | Audit-Trail |

### 2.4 Vorhandene Frontend-Views

```
App.tsx              → Session-Management, Sidebar-Navigation, View-Routing
LoginScreen.tsx      → Login-Formular
DashboardView.tsx    → Statistiken + Warnungen (gleich für alle Rollen)
AnimalsView.tsx      → Tierliste + Anlegen (Admin/Keeper)
SpeciesView.tsx      → Artenliste + Anlegen (Admin)
EnclosuresView.tsx   → Gehegeliste + Anlegen (Admin)
FeedingsView.tsx     → Fütterungspläne + Anlegen (Admin/Keeper)
HealthView.tsx       → Gesundheitseinträge + Anlegen (Admin/Vet)
TasksView.tsx        → Aufgabenliste + Anlegen (Admin/Keeper/Vet)
AuditView.tsx        → Audit-Logs (Admin)
```

### 2.5 Vorhandene Frontend-Komponenten

```
DataWorkspace.tsx    → View-Dispatcher (switch auf view-key)
Panel.tsx            → Panel-Container mit Icon + Titel
Icon.tsx             → 13 SVG-Icons als Inline-Paths
Lists.tsx            → CompactAnimalTable, TaskList, FeedingList
StatusChip.tsx       → Farbige Status-Badges
useWorkspaceData.ts  → Centralized Data-Fetching Hook
```

---

## 3. Schwächen & Fehler — Kritische Analyse

### 3.1 🔴 Kritische Schwächen (Sicherheit / Datenintegrität)

#### SW-001: Keine rollen-spezifische Datenfilterung
**Beschreibung:** Alle authentifizierten User sehen **alle** Tiere, Gehege, Aufgaben, Fütterungspläne. Ein Keeper sieht Tiere, die er nicht betreut. Ein Vet sieht Gesundheitsakten aller Tiere, nicht nur seine eigenen.

**Impact:** Datenschutz-Verletzung, Verwirrung im Betrieb, Keeper könnten versehentlich falsche Tiere füttern.

**Beispiel aus Code:**
```python
# backend/app/main.py:241-256
@app.get("/animals", response_model=list[AnimalRead])
def list_animals(...):
    return db.query(Animal).filter(Animal.active.is_(True)).order_by(...).all()
    # KEINE Rollen-Filterung!
```

**Fix-Strategie:**
- Phase 2: `animal_assignments` + `enclosure_assignments` Tabellen einführen
- Alle Listen-Endpunkte müssen nach `current_user.id` filtern (außer Admin)

---

#### SW-002: `viewer` Rolle hat keinen eingeschränkten API-Zugriff
**Beschreibung:** Viewer kann zwar keine Mutationen ausführen, aber sieht interne Daten (Fütterungspläne, Gesundheitsstatus, Aufgaben). Es gibt keine **Public API** für Besucher.

**Impact:** Interne Betriebsdaten sind für Besucher sichtbar.

**Fix-Strategie:**
- Phase 5: `/api/public/*` Endpunkte erstellen, die nur öffentliche Daten liefern
- Interne Endpunkte für Viewer blockieren (403)

---

#### SW-003: Keine Input-Sanitization bei Freitext-Feldern
**Beschreibung:** `description`, `notes`, `medication` Felder werden direkt in die DB geschrieben ohne XSS-Schutz. Obwohl React automatisch escaped, könnte ein API-Client (nicht das React-Frontend) bösartige Daten einspielen.

**Impact:** Potenzielle XSS bei zukünftigen Frontend-Erweiterungen oder API-Nutzung.

**Fix-Strategie:**
- HTML-Escaping im Backend vor dem Speichern
- Oder: Content-Security-Policy Header erweitern

---

#### SW-004: `tasks` hat keinen `assigned_to_user_id`
**Beschreibung:** Tasks haben nur `assigned_role` (keeper/vet/admin), aber keine konkrete User-Zuweisung. Ein Keeper sieht ALLE Keeper-Aufgaben, nicht nur seine eigenen.

**Impact:** Keeper können nicht ihren persönlichen Arbeitsplan sehen.

**Fix-Strategie:**
- Phase 3: `care_tasks` Tabelle mit `assigned_to_user_id` einführen
- ODER: `tasks` Tabelle um `assigned_to_user_id` erweitern

---

### 3.2 🟡 Architektonische Schwächen

#### SW-005: Monolithisches `main.py` (549 Zeilen)
**Beschreibung:** Alle API-Endpunkte, Hilfsfunktionen, App-Factory sind in einer Datei. Bei Erweiterung auf 30+ Endpunkte wird das unübersichtlich.

**Impact:** Wartbarkeit leidet, Merge-Konflikte, schwer zu testen.

**Fix-Strategie:**
- Router-Modularisierung: `routers/animals.py`, `routers/tasks.py`, etc.
- ODER: Zumindest pro Phase neue Router-Dateien erstellen

---

#### SW-006: Frontend hat kein Routing (nur View-State)
**Beschreibung:** Die App nutzt kein React Router — Views werden per `useState` gewechselt. Keine URL-basierte Navigation, kein Browser-Back-Button-Support, keine Deep-Links.

**Impact:** Schlechte UX, nicht teilbare Links, Refresh verliert den View.

**Fix-Strategie:**
- Phase 1: `react-router-dom` einführen
- URL-basierte Navigation: `/admin/dashboard`, `/keeper/calendar`, etc.

---

#### SW-007: `useWorkspaceData` lädt ALLE Daten für JEDEN View
**Beschreibung:** Der Hook lädt Dashboard, Animals, Species, Enclosures, Tasks, Feedings, HealthRecords, AuditLogs — unabhängig vom aktuellen View. Das ist ineffizient und wird mit wachsenden Daten langsam.

**Impact:** Unnötige API-Calls, langsame UI.

**Fix-Strategie:**
- View-spezifisches Lazy-Loading
- ODER: React Router + Route-spezifische Data-Loader

---

#### SW-008: Keine Pagination bei Listen-Endpunkten
**Beschreibung:** Obwohl `offset`/`limit` Parameter existieren, werden sie vom Frontend nicht genutzt. Bei 1000+ Tieren/Tieren wird die UI langsam.

**Impact:** Skalierbarkeitsproblem.

**Fix-Strategie:**
- Frontend: Virtual Scrolling oder Pagination-Controls
- Backend: Pagination-Metadaten (total_count, next_offset)

---

#### SW-009: SQLite als Produktions-DB
**Beschreibung:** Die App nutzt SQLite (`zoo.db`). Alembic ist konfiguriert, aber SQLite hat Einschränkungen (kein `ALTER COLUMN`, keine echten Foreign-Key-Constraints ohne PRAGMA).

**Impact:** Migrationen können bei komplexen Schema-Änderungen scheitern.

**Fix-Strategie:**
- Für Uni-Projekt: SQLite bleibt, aber Migrationen sorgfältig testen
- Für Produktion: PostgreSQL empfohlen

---

### 3.3 🟢 Verbesserungspotenzial (Qualität / UX)

#### SW-010: Keine Formular-Validierung im Frontend
**Beschreibung:** Formulare haben nur HTML5-Validierung (`required`, `minLength`). Keine client-seitige Business-Logik-Validierung (z.B. Geburtsdatum in der Zukunft).

**Fix-Strategie:**
- Zod oder Yup für Schema-Validierung einführen
- ODER: Manuelle Validierung vor dem Submit

---

#### SW-011: Keine Error Boundaries im Frontend
**Beschreibung:** Ein React-Render-Fehler crasht die gesamte App. Keine `ErrorBoundary` vorhanden.

**Fix-Strategie:**
- React Error Boundaries um DataWorkspace und einzelne Views wrappen

---

#### SW-012: Keine Loading-States pro View
**Beschreibung:** Es gibt nur einen globalen `isLoading` Zustand. Wenn ein View wechselt, flackert der gesamte Screen.

**Fix-Strategie:**
- View-spezifische Loading-States
- Skeleton-Loader statt "Daten werden geladen..."

---

#### SW-013: `FeedingSchedule` hat kein `due_date`, nur `scheduled_time`
**Beschreibung:** Fütterungspläne haben nur eine Uhrzeit (`09:00`), aber kein Datum. Es ist nicht klar, ob eine Fütterung "heute" oder "morgen" fällig ist.

**Fix-Strategie:**
- `FeedingSchedule` um `start_date`/`end_date` erweitern
- ODER: In Phase 3 durch `care_tasks` ersetzen

---

#### SW-014: `Animal` hat kein `age` Feld (berechnet)
**Beschreibung:** Das Frontend zeigt `birth_date ?? sex` an, aber nicht das Alter. Für Besucher-Map wichtig.

**Fix-Strategie:**
- Backend: `@property` für `age` in `Animal` Model
- ODER: Frontend-Berechnung aus `birth_date`

---

#### SW-015: Keine Bilder/Datei-Uploads
**Beschreibung:** Tiere, Gehege haben keine Bilder. Für eine Besucher-Map und Admin-Dashboard wären Fotos wertvoll.

**Fix-Strategie:**
- Optional: `image_url` Feld in `animals` und `enclosures`
- ODER: Base64-Images in DB (nicht empfohlen für große Bilder)

---

### 3.4 🟣 Code-Smells

#### SW-016: `Task.assigned_role` vs. `Task.assigned_to_user_id`
**Beschreibung:** Die aktuelle `tasks` Tabelle hat `assigned_role` (Enum), aber keine User-Zuweisung. Das Zielbild fordert `assigned_to_user_id` in `care_tasks` und `vet_tasks`.

**Entscheidung nötig:**
- Option A: `tasks` Tabelle erweitern (breaking change für bestehende Daten)
- Option B: Neue Tabellen `care_tasks` + `vet_tasks` erstellen (sauberer, aber mehr Komplexität)

**Empfehlung:** Option B — die aktuellen `tasks` sind generisch und bleiben als "System-Aufgaben" erhalten. Neue Tabellen für operative Aufgaben.

---

#### SW-017: `FeedingSchedule` vs. `care_tasks`
**Beschreibung:** `FeedingSchedule` ist ein wiederkehrender Plan, `care_tasks` sind konkrete Tagesaufgaben. Beide existieren parallel im Zielbild.

**Entscheidung nötig:**
- `FeedingSchedule` bleibt als "Planungs-Tool" (Admin)
- `care_tasks` werden aus `FeedingSchedule` generiert (oder manuell erstellt)

---

#### SW-018: `HealthRecord` vs. `medical_reports`
**Beschreibung:** `HealthRecord` ist ein generischer Gesundheitseintrag. `medical_reports` im Zielbild ist spezifischer (Diagnose, Behandlung, Medikamente, Nachkontrolle).

**Entscheidung nötig:**
- `HealthRecord` bleibt als "Quick-Notes" (Keeper kann Auffälligkeiten melden)
- `medical_reports` wird für Tierarzt-Dokumentation genutzt

---

## 4. Gap-Analyse: Aktueller Stand vs. Zielbild

### 4.1 Übersicht pro Phase

| Phase | Ziel | Aktueller Stand | Gap |
|-------|------|-----------------|-----|
| **1** | Rollen-Navigation | Alle sehen gleiche Sidebar + Dashboard | 🔴 Komplett fehlend |
| **2** | Zuweisungen (Tiere/Gehege ↔ Mitarbeiter) | Keine Zuweisungstabellen | 🔴 Komplett fehlend |
| **3** | Pflegekalender (Keeper) | Generische Tasks mit `assigned_role` | 🔴 Komplett fehlend |
| **4** | Tierarztkalender | Generische HealthRecords | 🟡 Teilweise vorhanden, aber nicht rollen-spezifisch |
| **5** | Besucher-Map | Keine Map, keine Public API | 🔴 Komplett fehlend |
| **6** | Wirtschaftsdashboard | Keine Wirtschaftsdaten | 🔴 Komplett fehlend |

### 4.2 Detaillierte Gap-Matrix

#### Phase 1 — Rollen-Navigation

| Feature | Status | Dateien betroffen |
|---------|--------|-------------------|
| Admin-Dashboard (`/admin`) | ❌ Fehlend | `App.tsx`, `constants.ts`, `main.py` |
| Keeper-Dashboard (`/keeper`) | ❌ Fehlend | `App.tsx`, `constants.ts`, neue Views |
| Vet-Dashboard (`/vet`) | ❌ Fehlend | `App.tsx`, `constants.ts`, neue Views |
| Visitor-Map (`/visitor`) | ❌ Fehlend | `App.tsx`, `constants.ts`, neue Views |
| React Router Integration | ❌ Fehlend | `App.tsx`, `main.tsx` |
| Rollen-spezifische Navigation | ❌ Fehlend | `constants.ts`, `App.tsx` |
| Redirect nach Login basierend auf Rolle | ❌ Fehlend | `LoginScreen.tsx`, `App.tsx` |

#### Phase 2 — Zuweisungen

| Feature | Status | Dateien betroffen |
|---------|--------|-------------------|
| `animal_assignments` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `enclosure_assignments` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| Admin-Zuweisungs-UI | ❌ Fehlend | Neue View/Component |
| Keeper sieht nur eigene Tiere | ❌ Fehlend | `main.py` (Filter), `AnimalsView.tsx` |
| Vet sieht nur medizinische Tiere | ❌ Fehlend | `main.py` (Filter), `HealthView.tsx` |

#### Phase 3 — Pflegekalender

| Feature | Status | Dateien betroffen |
|---------|--------|-------------------|
| `care_tasks` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `animal_condition_reports` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| Tagesansicht für Keeper | ❌ Fehlend | Neue View |
| Aufgabe abhaken | ❌ Fehlend | `care_tasks` API + UI |
| Zustandsbogen-Formular | ❌ Fehlend | Neue Component |
| Task-Generierung aus FeedingSchedule | ❌ Fehlend | Backend-Logik |

#### Phase 4 — Tierarztkalender

| Feature | Status | Dateien betroffen |
|---------|--------|-------------------|
| `vet_tasks` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `medical_reports` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| Medizinischer Kalender (Vet) | ❌ Fehlend | Neue View |
| Prioritäts-System (low/medium/high/emergency) | ❌ Fehlend | `models.py`, UI |
| Admin-Warnungen (Dashboard) | ❌ Fehlend | `DashboardView.tsx` |

#### Phase 5 — Besucher-Map

| Feature | Status | Dateien betroffen |
|---------|--------|-------------------|
| `map_x`, `map_y`, `map_width`, `map_height` in `enclosures` | ❌ Fehlend | `models.py`, Alembic-Migration |
| `public_name`, `public_description`, `is_public_visible` | ❌ Fehlend | `models.py`, Alembic-Migration |
| `map_paths` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| SVG/Canvas Zoo-Map | ❌ Fehlend | Neue Component |
| Public API (`/api/public/*`) | ❌ Fehlend | `main.py` |
| Besucher-UI (kein Login nötig) | ❌ Fehlend | Neue Route |

#### Phase 6 — Wirtschaftsdashboard

| Feature | Status | Dateien betroffen |
|---------|--------|-------------------|
| `visitor_stats` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `work_sessions` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `salary_profiles` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `food_items` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `animal_nutrition_requirements` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| `feeding_plans` Tabelle | ❌ Fehlend | `models.py`, Alembic-Migration |
| Besucherzahlen-Diagramm | ❌ Fehlend | Neue View + Chart-Lib |
| Gehaltsabrechnungs-Rechner | ❌ Fehlend | Neue View |
| Futterkosten-Optimierung (scipy.linprog) | ❌ Fehlend | Neue API + View |

---

## 5. Detaillierter Implementierungsplan

### 5.1 Vorbereitung (Vor Phase 1)

#### Schritt V1: Projekt-Struktur aufbereiten

**Backend:**
```
backend/
  app/
    __init__.py
    database.py          # (bestehend)
    main.py              # (bestehend, später aufgeteilt)
    models.py            # (bestehend, erweitern)
    schemas.py           # (bestehend, erweitern)
    security.py          # (bestehend)
    seed.py              # (bestehend, erweitern)
    routers/             # NEU
      __init__.py
      auth.py
      animals.py
      enclosures.py
      species.py
      tasks.py
      health.py
      feedings.py
      audit.py
      public.py          # Phase 5
      admin.py           # Phase 6
      keeper.py          # Phase 3
      vet.py             # Phase 4
    services/            # NEU (Business-Logik)
      __init__.py
      assignment_service.py
      task_service.py
      nutrition_optimizer.py  # Phase 6
```

**Frontend:**
```
frontend/src/
  App.tsx                # (bestehend, um Router erweitern)
  main.tsx               # (bestehend, RouterProvider)
  api.ts                 # (bestehend, erweitern)
  types.ts               # (bestehend, erweitern)
  constants.ts           # (bestehend, erweitern)
  styles.css             # (bestehend, erweitern)
  router.tsx             # NEU (react-router-dom)
  routes/                # NEU
    AdminRoute.tsx
    KeeperRoute.tsx
    VetRoute.tsx
    VisitorRoute.tsx
  views/                 # (bestehend)
    admin/               # NEU
      AdminDashboard.tsx
      AdminAssignments.tsx
      AdminEconomy.tsx
      AdminVisitorStats.tsx
    keeper/              # NEU
      KeeperCalendar.tsx
      KeeperMyAnimals.tsx
      KeeperConditionReport.tsx
    vet/                 # NEU
      VetCalendar.tsx
      VetMedicalReport.tsx
      VetCriticalAnimals.tsx
    visitor/             # NEU
      VisitorMap.tsx
      VisitorEnclosure.tsx
      VisitorAnimalInfo.tsx
  components/            # (bestehend)
    map/                 # NEU
      ZooMap.tsx
      MapEnclosure.tsx
      MapPath.tsx
    charts/              # NEU (Phase 6)
      VisitorChart.tsx
      CostChart.tsx
```

#### Schritt V2: Dependencies prüfen

**Backend Dependencies zu prüfen:**
```
# Aktuell:
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
SQLAlchemy>=2.0,<3.0
alembic>=1.13,<2.0
pydantic[email]>=2.8,<3.0
pwdlib[argon2]
PyJWT>=2.8,<3.0
pytest>=8.0,<9.0
httpx>=0.27,<1.0

# Neue für Phase 6 (Futter-Optimierung):
scipy>=1.12          # linprog
numpy>=1.26          # Array-Operationen

# Neue für Diagramme (optional, wenn Backend rendert):
# matplotlib>=3.8    # Nur wenn Backend Bilder rendert
```

**Frontend Dependencies zu prüfen:**
```
# Aktuell:
react: ^19.2.1
react-dom: ^19.2.1
vite: ^7.2.7

# Neue für Phase 1 (Routing):
react-router-dom: ^7.x

# Neue für Phase 6 (Diagramme):
# Option A: recharts (React-komponentenbasiert)
recharts: ^2.x
# Option B: chart.js + react-chartjs-2
chart.js: ^4.x
react-chartjs-2: ^5.x

# Neue für Formular-Validierung (optional):
zod: ^3.x
@hookform/resolvers: ^3.x
react-hook-form: ^7.x
```

---

### 5.2 Phase 1 — Rollen sinnvoll machen

#### Ziel
Nach Login landet jede Rolle auf der richtigen Oberfläche mit rollen-spezifischer Navigation.

#### Backend-Änderungen

**1.1 Neue API-Endpunkte (pro Rolle)**

```python
# app/routers/admin.py
@router.get("/admin/dashboard")
def admin_dashboard(current_user: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)):
    # Erweitertes Dashboard mit Zuweisungs-Übersicht
    ...

# app/routers/keeper.py
@router.get("/keeper/calendar")
def keeper_calendar(current_user: User = Depends(require_roles(UserRole.keeper)), db: Session = Depends(get_db)):
    # Tagesaufgaben für den eingeloggten Keeper
    ...

@router.get("/keeper/my-animals")
def keeper_my_animals(current_user: User = Depends(require_roles(UserRole.keeper)), db: Session = Depends(get_db)):
    # Tiere, die dem Keeper zugewiesen sind
    ...

# app/routers/vet.py
@router.get("/vet/calendar")
def vet_calendar(current_user: User = Depends(require_roles(UserRole.vet)), db: Session = Depends(get_db)):
    # Medizinische Aufgaben für den Vet
    ...

# app/routers/public.py (Phase 5, aber schon vorbereiten)
@router.get("/public/map")
def public_map(db: Session = Depends(get_db)):
    # Öffentliche Gehege-Daten
    ...
```

**1.2 `main.py` anpassen**

```python
# In create_app():
from .routers import admin, keeper, vet, public

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(keeper.router, prefix="/keeper", tags=["keeper"])
app.include_router(vet.router, prefix="/vet", tags=["vet"])
app.include_router(public.router, prefix="/public", tags=["public"])
```

#### Frontend-Änderungen

**1.3 React Router einführen**

```tsx
// router.tsx
import { createBrowserRouter, Navigate } from "react-router-dom";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { path: "admin/*", element: <AdminLayout /> },
      { path: "keeper/*", element: <KeeperLayout /> },
      { path: "vet/*", element: <VetLayout /> },
      { path: "visitor/*", element: <VisitorLayout /> },
      { path: "login", element: <LoginScreen /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
```

**1.4 Login-Redirect basierend auf Rolle**

```tsx
// LoginScreen.tsx oder App.tsx
const handleLogin = useCallback((nextSession: Session) => {
  setSession(nextSession);
  // Redirect basierend auf Rolle
  switch (nextSession.role) {
    case "admin": navigate("/admin"); break;
    case "keeper": navigate("/keeper"); break;
    case "vet": navigate("/vet"); break;
    case "viewer": navigate("/visitor"); break;
  }
}, [navigate]);
```

**1.5 Rollen-spezifische Navigation**

```ts
// constants.ts — erweitern
export const adminNavItems = [
  { key: "dashboard", label: "Dashboard", icon: "grid" as IconName, path: "/admin" },
  { key: "animals", label: "Tiere", icon: "paw" as IconName, path: "/admin/animals" },
  { key: "enclosures", label: "Gehege", icon: "shield" as IconName, path: "/admin/enclosures" },
  { key: "staff", label: "Mitarbeiter", icon: "users" as IconName, path: "/admin/staff" },
  { key: "assignments", label: "Zuweisungen", icon: "link" as IconName, path: "/admin/assignments" },
  { key: "care-reports", label: "Pflegeberichte", icon: "clipboard" as IconName, path: "/admin/care-reports" },
  { key: "vet-reports", label: "Tierarztberichte", icon: "heart" as IconName, path: "/admin/vet-reports" },
  { key: "economy", label: "Wirtschaft", icon: "dollar" as IconName, path: "/admin/economy" },
  { key: "visitor-stats", label: "Besucherstatistik", icon: "users" as IconName, path: "/admin/visitor-stats" },
];

export const keeperNavItems = [
  { key: "calendar", label: "Mein Kalender", icon: "calendar" as IconName, path: "/keeper" },
  { key: "my-animals", label: "Meine Tiere", icon: "paw" as IconName, path: "/keeper/my-animals" },
  { key: "open-tasks", label: "Offene Aufgaben", icon: "check" as IconName, path: "/keeper/open-tasks" },
  { key: "done-tasks", label: "Erledigte Aufgaben", icon: "check-circle" as IconName, path: "/keeper/done-tasks" },
  { key: "condition-reports", label: "Zustandsberichte", icon: "clipboard" as IconName, path: "/keeper/condition-reports" },
];

export const vetNavItems = [
  { key: "calendar", label: "Medizinischer Kalender", icon: "calendar" as IconName, path: "/vet" },
  { key: "examinations", label: "Untersuchungen", icon: "stethoscope" as IconName, path: "/vet/examinations" },
  { key: "treatment-reports", label: "Behandlungsberichte", icon: "file-text" as IconName, path: "/vet/treatment-reports" },
  { key: "critical-animals", label: "Kritische Tiere", icon: "alert" as IconName, path: "/vet/critical-animals" },
];

export const visitorNavItems = [
  { key: "map", label: "Zoo-Map", icon: "map" as IconName, path: "/visitor" },
  { key: "enclosures", label: "Gehege", icon: "shield" as IconName, path: "/visitor/enclosures" },
  { key: "animal-info", label: "Tierinfos", icon: "paw" as IconName, path: "/visitor/animal-info" },
];
```

**1.6 Neue Icons hinzufügen**

```tsx
// Icon.tsx — erweitern
export type IconName =
  | "grid" | "paw" | "leaf" | "shield" | "clock" | "heart" | "check"
  | "file" | "logout" | "login" | "plus" | "alert" | "trash"
  | "calendar" | "users" | "link" | "clipboard" | "dollar"
  | "check-circle" | "stethoscope" | "file-text" | "map";  // NEU
```

---

### 5.3 Phase 2 — Zuweisungen: Tiere und Gehege an Mitarbeiter binden

#### Ziel
Admin kann Keeper/Vet zu Tieren und Gehegen zuweisen. Keeper/Vet sehen nur ihre zugewiesenen Objekte.

#### Datenbank-Änderungen

**2.1 Neue Modelle (`models.py`)**

```python
class AnimalAssignment(Base):
    __tablename__ = "animal_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "keeper" | "vet"
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="animal_assignments")


class EnclosureAssignment(Base):
    __tablename__ = "enclosure_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    enclosure: Mapped[Enclosure] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="enclosure_assignments")
```

**2.2 Relationships erweitern**

```python
# In Animal:
assignments: Mapped[list["AnimalAssignment"]] = relationship(back_populates="animal", cascade="all, delete-orphan")

# In Enclosure:
assignments: Mapped[list["EnclosureAssignment"]] = relationship(back_populates="enclosure", cascade="all, delete-orphan")

# In User:
animal_assignments: Mapped[list["AnimalAssignment"]] = relationship(foreign_keys="AnimalAssignment.user_id", back_populates="user")
enclosure_assignments: Mapped[list["EnclosureAssignment"]] = relationship(foreign_keys="EnclosureAssignment.user_id", back_populates="user")
```

**2.3 Alembic-Migration erstellen**

```bash
cd backend
alembic revision -m "add animal and enclosure assignments"
# Migration manuell schreiben (oder autogenerate)
```

**2.4 Schemas erweitern (`schemas.py`)**

```python
class AnimalAssignmentCreate(BaseModel):
    animal_id: int
    user_id: int
    role_type: Literal["keeper", "vet"]

class AnimalAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    animal_id: int
    user_id: int
    role_type: str
    assigned_by: int | None
    created_at: datetime
    active: bool

class EnclosureAssignmentCreate(BaseModel):
    enclosure_id: int
    user_id: int

class EnclosureAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    enclosure_id: int
    user_id: int
    assigned_by: int | None
    created_at: datetime
    active: bool
```

**2.5 API-Endpunkte**

```python
# Admin-only Endpunkte
@app.post("/admin/animal-assignments", response_model=AnimalAssignmentRead)
def create_animal_assignment(...)

@app.delete("/admin/animal-assignments/{id}")
def delete_animal_assignment(...)

@app.post("/admin/enclosure-assignments", response_model=EnclosureAssignmentRead)
def create_enclosure_assignment(...)

@app.delete("/admin/enclosure-assignments/{id}")
def delete_enclosure_assignment(...)

@app.get("/admin/assignments")
def list_all_assignments(...)  # Für Admin-Übersicht

# Filtered Endpunkte (für Keeper/Vet)
@app.get("/keeper/my-animals", response_model=list[AnimalRead])
def keeper_my_animals(current_user: User = Depends(require_roles(UserRole.keeper)), db: Session = Depends(get_db)):
    assigned_animal_ids = select(AnimalAssignment.animal_id).where(
        AnimalAssignment.user_id == current_user.id,
        AnimalAssignment.active.is_(True)
    )
    return db.query(Animal).filter(Animal.id.in_(assigned_animal_ids), Animal.active.is_(True)).all()

@app.get("/vet/my-animals", response_model=list[AnimalRead])
def vet_my_animals(current_user: User = Depends(require_roles(UserRole.vet)), db: Session = Depends(get_db)):
    assigned_animal_ids = select(AnimalAssignment.animal_id).where(
        AnimalAssignment.user_id == current_user.id,
        AnimalAssignment.role_type == "vet",
        AnimalAssignment.active.is_(True)
    )
    return db.query(Animal).filter(Animal.id.in_(assigned_animal_ids), Animal.active.is_(True)).all()
```

**2.6 Bestehende Endpunkte anpassen**

```python
# /animals — für Keeper/Vet filtern
@app.get("/animals", response_model=list[AnimalRead])
def list_animals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ...
) -> Sequence[Animal]:
    query = db.query(Animal).filter(Animal.active.is_(True))
    
    if current_user.role == UserRole.keeper:
        assigned_ids = select(AnimalAssignment.animal_id).where(
            AnimalAssignment.user_id == current_user.id,
            AnimalAssignment.active.is_(True)
        )
        query = query.filter(Animal.id.in_(assigned_ids))
    elif current_user.role == UserRole.vet:
        assigned_ids = select(AnimalAssignment.animal_id).where(
            AnimalAssignment.user_id == current_user.id,
            AnimalAssignment.role_type == "vet",
            AnimalAssignment.active.is_(True)
        )
        query = query.filter(Animal.id.in_(assigned_ids))
    # Admin sieht alles (kein Filter)
    
    return query.order_by(Animal.name.asc()).offset(offset).limit(limit).all()
```

#### Frontend-Änderungen

**2.7 Admin-Zuweisungs-UI**

```tsx
// views/admin/AdminAssignments.tsx
// - Tier-Auswahl-Dropdown
// - Keeper-Auswahl-Dropdown
// - Vet-Auswahl-Dropdown
// - "Zuweisen" Button
// - Liste aktiver Zuweisungen mit "Entfernen" Button
```

**2.8 Tier-Detailansicht erweitern**

```tsx
// In AnimalsView.tsx oder neue AnimalDetailView.tsx
// - Zeige zugewiesenen Keeper
// - Zeige zugewiesenen Vet
// - Admin kann Zuweisung ändern
```

---

### 5.4 Phase 3 — Pflegekalender für Keeper

#### Ziel
Keeper sieht einen tagesbasierten Arbeitsplan mit abhakbaren Aufgaben und Zustandsbögen.

#### Datenbank-Änderungen

**3.1 Neue Tabelle: `care_tasks`**

```python
class CareTaskStatus(str, Enum):
    open = "open"
    done = "done"
    missed = "missed"

class CareTaskType(str, Enum):
    feeding = "feeding"
    cleaning = "cleaning"
    health_check = "health_check"
    enrichment = "enrichment"
    custom = "custom"

class CareTask(Base):
    __tablename__ = "care_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    animal_id: Mapped[int | None] = mapped_column(ForeignKey("animals.id", ondelete="SET NULL"))
    enclosure_id: Mapped[int | None] = mapped_column(ForeignKey("enclosures.id", ondelete="SET NULL"))
    assigned_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type: Mapped[CareTaskType] = mapped_column(SAEnum(CareTaskType), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_time: Mapped[time | None] = mapped_column(Time)
    status: Mapped[CareTaskStatus] = mapped_column(SAEnum(CareTaskStatus), default=CareTaskStatus.open, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal | None] = relationship()
    enclosure: Mapped[Enclosure | None] = relationship()
    assigned_to: Mapped[User] = relationship(foreign_keys=[assigned_to_user_id])
```

**3.2 Neue Tabelle: `animal_condition_reports`**

```python
class Mood(str, Enum):
    normal = "normal"
    nervous = "nervous"
    aggressive = "aggressive"
    tired = "tired"
    playful = "playful"

class Appetite(str, Enum):
    normal = "normal"
    low = "low"
    high = "high"
    refused = "refused"

class Movement(str, Enum):
    normal = "normal"
    limping = "limping"
    weak = "weak"
    hyperactive = "hyperactive"

class AnimalConditionReport(Base):
    __tablename__ = "animal_condition_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("care_tasks.id", ondelete="SET NULL"))
    mood: Mapped[Mood] = mapped_column(SAEnum(Mood), nullable=False)
    appetite: Mapped[Appetite] = mapped_column(SAEnum(Appetite), nullable=False)
    movement: Mapped[Movement] = mapped_column(SAEnum(Movement), nullable=False)
    visible_injuries: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    needs_vet_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship()
    created_by: Mapped[User] = relationship()
    task: Mapped[CareTask | None] = relationship()
```

**3.3 Schemas**

```python
class CareTaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    animal_id: int | None = None
    enclosure_id: int | None = None
    assigned_to_user_id: int
    task_type: CareTaskType
    due_date: date
    due_time: time | None = None

class CareTaskUpdate(BaseModel):
    status: CareTaskStatus | None = None
    # Nur Status-Update für Keeper (abhaken)

class AnimalConditionReportCreate(BaseModel):
    animal_id: int
    task_id: int | None = None
    mood: Mood
    appetite: Appetite
    movement: Movement
    visible_injuries: bool = False
    notes: str | None = Field(default=None, max_length=5000)
    needs_vet_check: bool = False
```

**3.4 API-Endpunkte**

```python
# Keeper-Endpunkte
@app.get("/keeper/calendar", response_model=list[CareTaskRead])
def keeper_calendar(
    date: date = Query(default_factory=date.today),
    current_user: User = Depends(require_roles(UserRole.keeper)),
    db: Session = Depends(get_db)
):
    return db.query(CareTask).filter(
        CareTask.assigned_to_user_id == current_user.id,
        CareTask.due_date == date
    ).order_by(CareTask.due_time.asc()).all()

@app.patch("/keeper/care-tasks/{task_id}/complete")
def complete_care_task(
    task_id: int,
    current_user: User = Depends(require_roles(UserRole.keeper)),
    db: Session = Depends(get_db)
):
    task = db.query(CareTask).filter(
        CareTask.id == task_id,
        CareTask.assigned_to_user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.status = CareTaskStatus.done
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    return task

@app.post("/keeper/condition-reports", response_model=AnimalConditionReportRead)
def create_condition_report(...)

# Admin-Endpunkte (Task-Verwaltung)
@app.post("/admin/care-tasks", response_model=CareTaskRead)
def create_care_task(...)

@app.delete("/admin/care-tasks/{task_id}")
def delete_care_task(...)
```

**3.5 Task-Generierung aus FeedingSchedule**

```python
# Service-Funktion (z.B. in services/task_service.py)
def generate_care_tasks_from_feeding_schedule(db: Session, target_date: date) -> None:
    """Generiert CareTasks aus FeedingSchedules für ein bestimmtes Datum."""
    schedules = db.query(FeedingSchedule).all()
    for schedule in schedules:
        # Prüfe, ob Task bereits existiert
        existing = db.query(CareTask).filter(
            CareTask.animal_id == schedule.animal_id,
            CareTask.due_date == target_date,
            CareTask.task_type == CareTaskType.feeding
        ).first()
        if existing:
            continue
        
        # Finde zugewiesenen Keeper
        assignment = db.query(AnimalAssignment).filter(
            AnimalAssignment.animal_id == schedule.animal_id,
            AnimalAssignment.role_type == "keeper",
            AnimalAssignment.active.is_(True)
        ).first()
        
        task = CareTask(
            title=f"{schedule.animal.name} füttern",
            description=f"{schedule.food_type} - {schedule.amount}",
            animal_id=schedule.animal_id,
            assigned_to_user_id=assignment.user_id if assignment else None,  # Fallback?
            task_type=CareTaskType.feeding,
            due_date=target_date,
            due_time=schedule.scheduled_time,
            created_by=1,  # System-User oder Admin
        )
        db.add(task)
    db.commit()
```

#### Frontend-Änderungen

**3.6 Keeper-Kalender-View**

```tsx
// views/keeper/KeeperCalendar.tsx
// - Datums-Auswahl (default: heute)
// - Liste der Aufgaben für den Tag
// - Checkbox zum Abhaken
// - "Zustandsbogen ausfüllen" Button pro Tier-Task

interface KeeperCalendarProps {
  session: Session;
}

export function KeeperCalendar({ session }: KeeperCalendarProps) {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [tasks, setTasks] = useState<CareTask[]>([]);
  
  // API: GET /keeper/calendar?date=2026-06-11
  
  return (
    <div className="view-stack">
      <Panel title="Pflegekalender" icon="calendar">
        <input 
          type="date" 
          value={selectedDate} 
          onChange={e => setSelectedDate(e.target.value)} 
        />
        <div className="task-list">
          {tasks.map(task => (
            <div key={task.id} className={`task-row ${task.status}`}>
              <input 
                type="checkbox" 
                checked={task.status === 'done'}
                onChange={() => handleComplete(task.id)}
              />
              <span>{task.due_time?.slice(0, 5)} {task.title}</span>
              {task.animal_id && (
                <button onClick={() => openConditionReport(task.animal_id, task.id)}>
                  Zustandsbogen
                </button>
              )}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
```

**3.7 Zustandsbogen-Formular**

```tsx
// views/keeper/KeeperConditionReport.tsx
// - Tier-Name (read-only)
// - Stimmung: Radio-Buttons (normal, nervous, aggressive, tired, playful)
// - Fressverhalten: Radio-Buttons (normal, low, high, refused)
// - Bewegung: Radio-Buttons (normal, limping, weak, hyperactive)
// - Auffälligkeiten: Textarea
// - "Tierarztprüfung nötig" Checkbox
// - "Bericht speichern" Button
```

---

### 5.5 Phase 4 — Tierarztkalender

#### Ziel
Vet sieht medizinische Aufgaben, dokumentiert Untersuchungen und Behandlungen.

#### Datenbank-Änderungen

**4.1 Neue Tabelle: `vet_tasks`**

```python
class VetTaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    emergency = "emergency"

class VetTaskStatus(str, Enum):
    open = "open"
    done = "done"
    cancelled = "cancelled"

class VetTask(Base):
    __tablename__ = "vet_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    assigned_to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    priority: Mapped[VetTaskPriority] = mapped_column(SAEnum(VetTaskPriority), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[VetTaskStatus] = mapped_column(SAEnum(VetTaskStatus), default=VetTaskStatus.open, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship()
    assigned_to: Mapped[User] = relationship(foreign_keys=[assigned_to_user_id])
```

**4.2 Neue Tabelle: `medical_reports`**

```python
class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    vet_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("vet_tasks.id", ondelete="SET NULL"))
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    treatment: Mapped[str | None] = mapped_column(Text)
    medication: Mapped[str | None] = mapped_column(Text)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    animal: Mapped[Animal] = relationship()
    vet: Mapped[User] = relationship()
    task: Mapped[VetTask | None] = relationship()
```

**4.3 API-Endpunkte**

```python
# Vet-Endpunkte
@app.get("/vet/calendar", response_model=list[VetTaskRead])
def vet_calendar(
    date: date = Query(default_factory=date.today),
    current_user: User = Depends(require_roles(UserRole.vet)),
    db: Session = Depends(get_db)
):
    return db.query(VetTask).filter(
        VetTask.assigned_to_user_id == current_user.id,
        VetTask.due_date == date
    ).order_by(
        case(
            (VetTask.priority == VetTaskPriority.emergency, 1),
            (VetTask.priority == VetTaskPriority.high, 2),
            (VetTask.priority == VetTaskPriority.medium, 3),
            (VetTask.priority == VetTaskPriority.low, 4),
        ).asc(),
    ).all()

@app.patch("/vet/tasks/{task_id}/complete")
def complete_vet_task(...)

@app.post("/vet/medical-reports", response_model=MedicalReportRead)
def create_medical_report(...)

# Admin-Warnungen
@app.get("/admin/warnings")
def admin_warnings(current_user: User = Depends(require_roles(UserRole.admin)), db: Session = Depends(get_db)):
    return {
        "vet_check_needed": db.query(AnimalConditionReport).filter(
            AnimalConditionReport.needs_vet_check.is_(True)
        ).count(),
        "high_priority_vet_tasks": db.query(VetTask).filter(
            VetTask.priority == VetTaskPriority.high,
            VetTask.status == VetTaskStatus.open
        ).count(),
        "open_care_reports": db.query(CareTask).filter(
            CareTask.status == CareTaskStatus.open
        ).count(),
    }
```

#### Frontend-Änderungen

**4.4 Vet-Kalender-View**

```tsx
// views/vet/VetCalendar.tsx
// - Datums-Auswahl
// - Liste medizinischer Aufgaben mit Prioritäts-Badge
// - "Dokumentieren" Button pro Task
// - Formular: Diagnose, Behandlung, Medikamente, Nachkontrolle
```

**4.5 Admin-Warnungen im Dashboard**

```tsx
// In AdminDashboard.tsx
// - Kachel: "3 Tiere benötigen Tierarztprüfung"
// - Kachel: "1 medizinischer Fall mit hoher Priorität"
// - Kachel: "5 offene Pflegeberichte"
```

---

### 5.6 Phase 5 — Besucher-Map

#### Ziel
Besucher sehen eine interaktive Zoo-Map ohne Login.

#### Datenbank-Änderungen

**5.1 `enclosures` erweitern**

```python
# In Enclosure Model:
map_x: Mapped[int | None] = mapped_column(Integer)
map_y: Mapped[int | None] = mapped_column(Integer)
map_width: Mapped[int | None] = mapped_column(Integer)
map_height: Mapped[int | None] = mapped_column(Integer)
public_name: Mapped[str | None] = mapped_column(String(120))
public_description: Mapped[str | None] = mapped_column(Text)
is_public_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

**5.2 Neue Tabelle: `map_paths`**

```python
class MapPath(Base):
    __tablename__ = "map_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    to_enclosure_id: Mapped[int] = mapped_column(ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False)
    distance_meters: Mapped[int | None] = mapped_column(Integer)
    walking_time_minutes: Mapped[int | None] = mapped_column(Integer)
    path_svg_data: Mapped[str | None] = mapped_column(Text)  # SVG path d-Attribut

    from_enclosure: Mapped[Enclosure] = relationship(foreign_keys=[from_enclosure_id])
    to_enclosure: Mapped[Enclosure] = relationship(foreign_keys=[to_enclosure_id])
```

**5.3 Public API (ohne Auth)**

```python
# app/routers/public.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/map")
def public_map(db: Session = Depends(get_db)):
    enclosures = db.query(Enclosure).filter(Enclosure.is_public_visible.is_(True)).all()
    paths = db.query(MapPath).all()
    return {
        "enclosures": [
            {
                "id": e.id,
                "public_name": e.public_name or e.name,
                "public_description": e.public_description,
                "x": e.map_x,
                "y": e.map_y,
                "width": e.map_width,
                "height": e.map_height,
            }
            for e in enclosures
        ],
        "paths": [
            {
                "from_id": p.from_enclosure_id,
                "to_id": p.to_enclosure_id,
                "svg_path": p.path_svg_data,
            }
            for p in paths
        ]
    }

@router.get("/enclosures/{enclosure_id}/animals")
def public_enclosure_animals(enclosure_id: int, db: Session = Depends(get_db)):
    enclosure = db.query(Enclosure).filter(
        Enclosure.id == enclosure_id,
        Enclosure.is_public_visible.is_(True)
    ).first()
    if not enclosure:
        raise HTTPException(404, "Enclosure not found")
    
    animals = db.query(Animal).filter(
        Animal.enclosure_id == enclosure_id,
        Animal.active.is_(True)
    ).all()
    
    return [
        {
            "id": a.id,
            "name": a.name,
            "species": a.species.common_name,
            "age": calculate_age(a.birth_date),  # Berechnetes Feld
            "scientific_name": a.species.scientific_name,
        }
        for a in animals
    ]
```

**WICHTIG:** Public API darf **NICHT** ausgeben:
- Interne IDs von Mitarbeitern
- Gesundheitsdaten
- Pflegeberichte
- Kosten
- Aufgaben
- Audit Logs

#### Frontend-Änderungen

**5.4 Besucher-Map Component**

```tsx
// views/visitor/VisitorMap.tsx
// - SVG-basierte Karte (800x600 ViewBox)
// - Rechtecke für Gehege (positioniert via map_x, map_y, map_width, map_height)
// - Linien für Wege (SVG paths)
// - Klick auf Gehege → Modal/Panel mit Tier-Infos
// - Kein Login nötig!

export function VisitorMap() {
  const [mapData, setMapData] = useState(null);
  const [selectedEnclosure, setSelectedEnclosure] = useState(null);
  
  useEffect(() => {
    fetch('/api/public/map').then(r => r.json()).then(setMapData);
  }, []);
  
  return (
    <div className="visitor-map">
      <svg viewBox="0 0 800 600">
        {/* Wege */}
        {mapData?.paths.map(p => (
          <path key={`${p.from_id}-${p.to_id}`} d={p.svg_path} className="map-path" />
        ))}
        {/* Gehege */}
        {mapData?.enclosures.map(e => (
          <g key={e.id} onClick={() => setSelectedEnclosure(e)} className="map-enclosure">
            <rect x={e.x} y={e.y} width={e.width} height={e.height} rx="8" />
            <text x={e.x + e.width/2} y={e.y + e.height/2}>{e.public_name}</text>
          </g>
        ))}
      </svg>
      {selectedEnclosure && <EnclosureDetailModal enclosure={selectedEnclosure} onClose={...} />}
    </div>
  );
}
```

**5.5 Besucher-Route (ohne Auth)**

```tsx
// App.tsx — Anpassung
// Visitor-Route rendert ohne Session-Check
// ODER: Separate App für Besucher

<Route path="/visitor/*" element={<VisitorLayout />} />
// VisitorLayout hat KEINE Sidebar, nur Header + Map
```

---

### 5.7 Phase 6 — Admin Management & Wirtschaft

#### Ziel
Admin-Wirtschaftsdashboard mit Besucherstatistik, Gehaltsabrechnung und Futterkosten-Optimierung.

#### Datenbank-Änderungen

**6.1 Neue Tabelle: `visitor_stats`**

```python
class VisitorStat(Base):
    __tablename__ = "visitor_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    visitor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    ticket_revenue: Mapped[float] = mapped_column(Integer, nullable=False)  # in Cent oder Euro
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
```

**6.2 Neue Tabelle: `work_sessions`**

```python
class WorkSession(Base):
    __tablename__ = "work_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    logout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), default="login", nullable=False)  # "login" | "manual"

    user: Mapped[User] = relationship()
```

**6.3 Neue Tabelle: `salary_profiles`**

```python
class SalaryProfile(Base):
    __tablename__ = "salary_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    hourly_rate: Mapped[float] = mapped_column(Integer, nullable=False)  # in Cent
    monthly_base_salary: Mapped[float | None] = mapped_column(Integer)  # in Cent
    tax_rate_percent: Mapped[float | None] = mapped_column(Integer)  # z.B. 20.0 für 20%
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship()
```

**6.4 Neue Tabelle: `food_items`**

```python
class FoodItem(Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # "kg", "g", "l"
    cost_per_unit: Mapped[float] = mapped_column(Integer, nullable=False)  # in Cent
    calories_per_unit: Mapped[float] = mapped_column(Integer, nullable=False)
    protein_per_unit: Mapped[float] = mapped_column(Integer, nullable=False)
    fat_per_unit: Mapped[float | None] = mapped_column(Integer)
    available_quantity: Mapped[float] = mapped_column(Integer, nullable=False)
```

**6.5 Neue Tabelle: `animal_nutrition_requirements`**

```python
class AnimalNutritionRequirement(Base):
    __tablename__ = "animal_nutrition_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id", ondelete="CASCADE"), nullable=False)
    min_calories: Mapped[float] = mapped_column(Integer, nullable=False)
    min_protein: Mapped[float] = mapped_column(Integer, nullable=False)
    max_fat: Mapped[float | None] = mapped_column(Integer)
    food_category: Mapped[str | None] = mapped_column(String(80))  # "carnivore", "herbivore", etc.

    species: Mapped[Species] = relationship()
```

**6.6 Neue Tabelle: `feeding_plans`**

```python
class FeedingPlan(Base):
    __tablename__ = "feeding_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"), nullable=False)
    food_item_id: Mapped[int] = mapped_column(ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(Integer, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_optimized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    animal: Mapped[Animal] = relationship()
    food_item: Mapped[FoodItem] = relationship()
```

#### API-Endpunkte

**6.7 Besucherstatistik**

```python
@app.post("/admin/visitor-stats")
def create_visitor_stat(...)

@app.get("/admin/visitor-stats")
def visitor_stats(
    start_date: date,
    end_date: date,
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db)
):
    return db.query(VisitorStat).filter(
        VisitorStat.date >= start_date,
        VisitorStat.date <= end_date
    ).order_by(VisitorStat.date.asc()).all()

@app.get("/admin/visitor-stats/summary")
def visitor_stats_summary(...):
    # Aggregierte Daten für Diagramme
    return {
        "daily": [...],
        "weekly": [...],
        "revenue_trend": [...]
    }
```

**6.8 Work Sessions (Login/Logout Tracking)**

```python
# In auth/login:
@app.post("/auth/login")
def login(...):
    # ... bestehender Code ...
    # Work Session starten
    db.add(WorkSession(
        user_id=user.id,
        login_at=datetime.now(timezone.utc),
        source="login"
    ))
    db.commit()
    return response

# In auth/logout:
@app.post("/auth/logout")
def logout(...):
    # ... bestehender Code ...
    # Work Session beenden
    session = db.query(WorkSession).filter(
        WorkSession.user_id == current_user.id,
        WorkSession.logout_at.is_(None)
    ).order_by(WorkSession.login_at.desc()).first()
    if session:
        session.logout_at = datetime.now(timezone.utc)
        session.duration_minutes = int((session.logout_at - session.login_at).total_seconds() / 60)
    db.commit()
    return response
```

**6.9 Gehaltsabrechnungs-Rechner**

```python
@app.get("/admin/salary-calculation/{user_id}")
def calculate_salary(
    user_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2030),
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db)
):
    profile = db.query(SalaryProfile).filter(SalaryProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Salary profile not found")
    
    # Arbeitszeit berechnen
    sessions = db.query(WorkSession).filter(
        WorkSession.user_id == user_id,
        WorkSession.login_at >= datetime(year, month, 1),
        WorkSession.login_at < datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    ).all()
    
    total_minutes = sum(s.duration_minutes or 0 for s in sessions)
    # Max 8h pro Session (falls kein Logout)
    total_hours = total_minutes / 60
    
    hourly_rate_eur = profile.hourly_rate / 100  # Cent → Euro
    gross = total_hours * hourly_rate_eur
    tax_rate = (profile.tax_rate_percent or 20.0) / 100
    deductions = gross * tax_rate
    net = gross - deductions
    
    return {
        "user_id": user_id,
        "month": month,
        "year": year,
        "total_hours": round(total_hours, 2),
        "hourly_rate": hourly_rate_eur,
        "gross": round(gross, 2),
        "deductions": round(deductions, 2),
        "net": round(net, 2),
        "is_simulation": True,  # WICHTIG: Als Simulation kennzeichnen!
        "disclaimer": "Dies ist eine vereinfachte Simulation, keine echte Lohnabrechnung."
    }
```

**6.10 Futterkosten-Optimierung (scipy.linprog)**

```python
from scipy.optimize import linprog
import numpy as np

@app.post("/admin/feeding-optimization")
def optimize_feeding(
    current_user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db)
):
    # 1. Alle aktiven Tiere holen
    animals = db.query(Animal).filter(Animal.active.is_(True)).options(
        joinedload(Animal.species)
    ).all()
    
    # 2. Alle Futtertypen holen
    food_items = db.query(FoodItem).all()
    
    # 3. Bedarfsmatrix aufbauen
    n_animals = len(animals)
    n_foods = len(food_items)
    
    # Kosten-Vektor (minimieren)
    c = [food.cost_per_unit for food in food_items]
    
    # Nebenbedingungen:
    # - Jedes Tier bekommt genug Kalorien
    # - Jedes Tier bekommt genug Protein
    # - Verfügbare Menge darf nicht überschritten werden
    
    A_ub = []  # ≤ constraints
    b_ub = []
    
    # Verfügbarkeits-Constraint (pro Futtertyp)
    for j, food in enumerate(food_items):
        row = [0] * n_foods
        row[j] = 1
        A_ub.append(row)
        b_ub.append(food.available_quantity)
    
    # Bedarfs-Constraints (pro Tier)
    A_eq = []  # = constraints
    b_eq = []
    
    for animal in animals:
        req = db.query(AnimalNutritionRequirement).filter(
            AnimalNutritionRequirement.species_id == animal.species_id
        ).first()
        if not req:
            continue
        
        # Kalorien-Constraint
        calories_row = [food.calories_per_unit for food in food_items]
        A_eq.append(calories_row)
        b_eq.append(req.min_calories)
        
        # Protein-Constraint
        protein_row = [food.protein_per_unit for food in food_items]
        A_eq.append(protein_row)
        b_eq.append(req.min_protein)
    
    # Lösen
    result = linprog(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=[(0, None) for _ in range(n_foods)],
        method='highs'
    )
    
    if not result.success:
        return {
            "success": False,
            "message": "Optimierung nicht möglich. Bedarfs-Constraints können nicht erfüllt werden.",
            "details": result.message
        }
    
    # Ergebnis aufbereiten
    feeding_plan = []
    for j, food in enumerate(food_items):
        if result.x[j] > 0.001:  # Nur signifikante Mengen
            feeding_plan.append({
                "food_item_id": food.id,
                "food_name": food.name,
                "quantity": round(result.x[j], 3),
                "unit": food.unit,
                "cost": round(result.x[j] * food.cost_per_unit / 100, 2)  # Cent → Euro
            })
    
    return {
        "success": True,
        "total_cost": round(result.fun / 100, 2),  # Cent → Euro
        "feeding_plan": feeding_plan,
        "method": "linear_programming",
        "solver": "scipy.optimize.linprog"
    }
```

#### Frontend-Änderungen

**6.11 Admin-Wirtschaftsdashboard**

```tsx
// views/admin/AdminEconomy.tsx
// - Kacheln:
//   - Besucher heute
//   - Besucher diese Woche
//   - Futterkosten pro Monat
//   - Personalkosten geschätzt
//   - Offene Aufgaben
//   - Tierarztfälle
//   - Kosten pro Tierart
```

**6.12 Besucherzahlen-Diagramm**

```tsx
// components/charts/VisitorChart.tsx
// - recharts oder chart.js
// - LineChart: Besucher pro Tag
// - BarChart: Umsatzentwicklung
// - Zeitraum-Auswahl (7 Tage, 30 Tage, 1 Jahr)
```

**6.13 Gehaltsabrechnungs-UI**

```tsx
// views/admin/AdminSalary.tsx
// - Mitarbeiter-Auswahl
// - Zeitraum-Auswahl
// - Ergebnis-Tabelle:
//   - Arbeitszeit: 126 Stunden
//   - Stundenlohn: 16,50 €
//   - Brutto: 2.079,00 €
//   - Abzüge geschätzt: 415,80 €
//   - Netto geschätzt: 1.663,20 €
// - WARNUNG-Badge: "Vereinfachte Simulation"
```

**6.14 Futterkosten-Optimierer-UI**

```tsx
// views/admin/AdminFeedingOptimizer.tsx
// - "Optimierung starten" Button
// - Lade-Animation
// - Ergebnis-Tabelle:
//   - Futtertyp | Menge | Einheit | Kosten
// - Gesamtkosten
// - Mathematische Erklärung (für Professor):
//   - "Minimiere: Kosten = Σ(Menge_i × Preis_i)"
//   - "Nebenbedingungen: Kalorien ≥ Bedarf, Protein ≥ Bedarf, Menge ≤ Lager"
```

---

## 6. Datenbank-Migrations-Plan

### Migration 0002: Animal & Enclosure Assignments

```python
"""add animal and enclosure assignments

Revision ID: 0002
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001_initial"

def upgrade():
    op.create_table(
        "animal_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_type", sa.String(20), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
    )
    op.create_index("ix_animal_assignments_user", "animal_assignments", ["user_id", "active"])
    op.create_index("ix_animal_assignments_animal", "animal_assignments", ["animal_id", "active"])
    
    op.create_table(
        "enclosure_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
    )
    op.create_index("ix_enclosure_assignments_user", "enclosure_assignments", ["user_id", "active"])

def downgrade():
    op.drop_index("ix_enclosure_assignments_user", table_name="enclosure_assignments")
    op.drop_table("enclosure_assignments")
    op.drop_index("ix_animal_assignments_animal", table_name="animal_assignments")
    op.drop_index("ix_animal_assignments_user", table_name="animal_assignments")
    op.drop_table("animal_assignments")
```

### Migration 0003: Care Tasks & Condition Reports

```python
"""add care tasks and animal condition reports

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"

def upgrade():
    caretaskstatus = sa.Enum("open", "done", "missed", name="caretaskstatus")
    caretasktype = sa.Enum("feeding", "cleaning", "health_check", "enrichment", "custom", name="caretasktype")
    mood = sa.Enum("normal", "nervous", "aggressive", "tired", "playful", name="mood")
    appetite = sa.Enum("normal", "low", "high", "refused", name="appetite")
    movement = sa.Enum("normal", "limping", "weak", "hyperactive", name="movement")
    
    op.create_table(
        "care_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_type", caretasktype, nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("due_time", sa.Time(), nullable=True),
        sa.Column("status", caretaskstatus, nullable=False, default="open"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_care_tasks_assigned_date", "care_tasks", ["assigned_to_user_id", "due_date", "status"])
    
    op.create_table(
        "animal_condition_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("care_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mood", mood, nullable=False),
        sa.Column("appetite", appetite, nullable=False),
        sa.Column("movement", movement, nullable=False),
        sa.Column("visible_injuries", sa.Boolean(), nullable=False, default=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("needs_vet_check", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    op.drop_table("animal_condition_reports")
    op.drop_index("ix_care_tasks_assigned_date", table_name="care_tasks")
    op.drop_table("care_tasks")
```

### Migration 0004: Vet Tasks & Medical Reports

```python
"""add vet tasks and medical reports

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"

def upgrade():
    vettaskpriority = sa.Enum("low", "medium", "high", "emergency", name="vettaskpriority")
    vettaskstatus = sa.Enum("open", "done", "cancelled", name="vettaskstatus")
    
    op.create_table(
        "vet_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", vettaskpriority, nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", vettaskstatus, nullable=False, default="open"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_vet_tasks_assigned_date", "vet_tasks", ["assigned_to_user_id", "due_date", "status"])
    
    op.create_table(
        "medical_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vet_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("vet_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("medication", sa.Text(), nullable=True),
        sa.Column("follow_up_required", sa.Boolean(), nullable=False, default=False),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    op.drop_table("medical_reports")
    op.drop_index("ix_vet_tasks_assigned_date", table_name="vet_tasks")
    op.drop_table("vet_tasks")
```

### Migration 0005: Enclosure Map Fields & Map Paths

```python
"""add enclosure map fields and map paths

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"

def upgrade():
    op.add_column("enclosures", sa.Column("map_x", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("map_y", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("map_width", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("map_height", sa.Integer(), nullable=True))
    op.add_column("enclosures", sa.Column("public_name", sa.String(120), nullable=True))
    op.add_column("enclosures", sa.Column("public_description", sa.Text(), nullable=True))
    op.add_column("enclosures", sa.Column("is_public_visible", sa.Boolean(), nullable=False, server_default="1"))
    
    op.create_table(
        "map_paths",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_enclosure_id", sa.Integer(), sa.ForeignKey("enclosures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distance_meters", sa.Integer(), nullable=True),
        sa.Column("walking_time_minutes", sa.Integer(), nullable=True),
        sa.Column("path_svg_data", sa.Text(), nullable=True),
    )

def downgrade():
    op.drop_table("map_paths")
    op.drop_column("enclosures", "is_public_visible")
    op.drop_column("enclosures", "public_description")
    op.drop_column("enclosures", "public_name")
    op.drop_column("enclosures", "map_height")
    op.drop_column("enclosures", "map_width")
    op.drop_column("enclosures", "map_y")
    op.drop_column("enclosures", "map_x")
```

### Migration 0006: Economy Tables

```python
"""add economy tables: visitor_stats, work_sessions, salary_profiles, food_items, nutrition_requirements, feeding_plans

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"

def upgrade():
    op.create_table(
        "visitor_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("visitor_count", sa.Integer(), nullable=False),
        sa.Column("ticket_revenue", sa.Integer(), nullable=False),  # in Cent
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    
    op.create_table(
        "work_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="login"),
    )
    op.create_index("ix_work_sessions_user", "work_sessions", ["user_id", "login_at"])
    
    op.create_table(
        "salary_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("hourly_rate", sa.Integer(), nullable=False),  # in Cent
        sa.Column("monthly_base_salary", sa.Integer(), nullable=True),
        sa.Column("tax_rate_percent", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
    )
    
    op.create_table(
        "food_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("cost_per_unit", sa.Integer(), nullable=False),  # in Cent
        sa.Column("calories_per_unit", sa.Integer(), nullable=False),
        sa.Column("protein_per_unit", sa.Integer(), nullable=False),
        sa.Column("fat_per_unit", sa.Integer(), nullable=True),
        sa.Column("available_quantity", sa.Integer(), nullable=False),
    )
    
    op.create_table(
        "animal_nutrition_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("species_id", sa.Integer(), sa.ForeignKey("species.id", ondelete="CASCADE"), nullable=False),
        sa.Column("min_calories", sa.Integer(), nullable=False),
        sa.Column("min_protein", sa.Integer(), nullable=False),
        sa.Column("max_fat", sa.Integer(), nullable=True),
        sa.Column("food_category", sa.String(80), nullable=True),
    )
    
    op.create_table(
        "feeding_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("food_item_id", sa.Integer(), sa.ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_optimized", sa.Boolean(), nullable=False, server_default="0"),
    )

def downgrade():
    op.drop_table("feeding_plans")
    op.drop_table("animal_nutrition_requirements")
    op.drop_table("food_items")
    op.drop_table("salary_profiles")
    op.drop_index("ix_work_sessions_user", table_name="work_sessions")
    op.drop_table("work_sessions")
    op.drop_table("visitor_stats")
```

---

## 7. Test-Strategie

### 7.1 Backend-Tests (pytest)

```python
# tests/test_assignments.py
# tests/test_care_tasks.py
# tests/test_vet_tasks.py
# tests/test_medical_reports.py
# tests/test_public_api.py
# tests/test_economy.py
# tests/test_feeding_optimizer.py
```

**Wichtige Testfälle:**

| Test | Beschreibung |
|------|--------------|
| `test_keeper_sees_only_assigned_animals` | Keeper bekommt nur seine Tiere |
| `test_vet_sees_only_medical_animals` | Vet bekommt nur seine medizinischen Tiere |
| `test_viewer_cannot_access_internal_api` | Viewer/Öffentlichkeit → 403 oder Public API |
| `test_public_api_excludes_internal_data` | Public API hat keine internen IDs, Gesundheitsdaten |
| `test_care_task_completion` | Keeper kann Task abhaken, Status ändert sich |
| `test_condition_report_triggers_vet_alert` | Zustandsbogen mit needs_vet_check → Admin-Warnung |
| `test_vet_task_priority_sorting` | Emergency > High > Medium > Low |
| `test_salary_calculation_is_simulation` | Response enthält `is_simulation: True` |
| `test_feeding_optimizer_respects_constraints` | linprog Ergebnis erfüllt alle Bedarfs-Constraints |
| `test_work_session_tracking` | Login erstellt Session, Logout beendet sie |

### 7.2 Frontend-Tests

```
# E2E-Tests (optional, z.B. Playwright):
- Login als Keeper → Redirect zu /keeper
- Keeper sieht nur "Meine Tiere"
- Keeper kann Task abhaken
- Visitor sieht Map ohne Login
- Admin kann Zuweisung erstellen
```

---

## 8. Risiken & Empfehlungen

### 8.1 Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| SQLite-Migrationen scheitern bei komplexen Änderungen | Mittel | Hoch | Jede Migration manuell testen; PostgreSQL für Produktion |
| Frontend-Routing-Refactoring bricht bestehende Views | Mittel | Mittel | Schrittweise einführen, alte View-State-Logik parallel lassen |
| scipy nicht installierbar auf Zielsystem | Niedrig | Hoch | Optionaler Import, Fallback auf manuelle Berechnung |
| Scope-Creep (zu viele Features auf einmal) | Hoch | Hoch | Strikte Phasen-Einteilung, eine Phase nach der anderen |
| Performance bei vielen Daten | Mittel | Mittel | Pagination, Lazy Loading, DB-Indizes |

### 8.2 Empfehlungen

1. **Eine Phase nach der anderen implementieren.** Nicht alles auf einmal.
2. **Jede Phase testen, bevor die nächste beginnt.**
3. **Backend-Router modularisieren** — `main.py` wird sonst unübersichtlich.
4. **React Router einführen** — verbessert UX erheblich.
5. **Für Uni-Abgabe:** Phasen 1-4 sind das "Must-Have". Phasen 5-6 sind "Nice-to-Have" für Bonus-Punkte.
6. **scipy für Futter-Optimierung** ist ein starker technischer Show-Case für den Professor.
7. **Besucher-Map als SVG** ist pragmatisch und wirkt trotzdem stark.
8. **Gehaltsabrechnung als "Simulation" kennzeichnen** — vermeidet rechtliche Probleme.

---

## 9. Zusammenfassung: Was wo implementiert werden muss

### Backend (`backend/app/`)

| Datei | Änderungen |
|-------|-----------|
| `models.py` | 6 neue Modelle + Erweiterungen an bestehenden |
| `schemas.py` | ~15 neue Pydantic-Modelle |
| `main.py` | Neue Router einbinden, bestehende Endpunkte filtern |
| `routers/*.py` | 10+ neue Router-Dateien |
| `services/*.py` | Business-Logik (Task-Generierung, Optimierung) |
| `seed.py` | Demo-Daten für neue Tabellen |
| `alembic/versions/` | 6 neue Migrationen |
| `tests/*.py` | 10+ neue Test-Dateien |
| `requirements.txt` | scipy, numpy hinzufügen |

### Frontend (`frontend/src/`)

| Datei | Änderungen |
|-------|-----------|
| `App.tsx` | Router-Integration, Rollen-Redirect |
| `main.tsx` | RouterProvider |
| `router.tsx` | NEU — Route-Definitionen |
| `api.ts` | ~20 neue API-Methoden |
| `types.ts` | ~15 neue Type-Definitionen |
| `constants.ts` | Rollen-spezifische Navigation |
| `views/admin/*.tsx` | 4+ neue Admin-Views |
| `views/keeper/*.tsx` | 3+ neue Keeper-Views |
| `views/vet/*.tsx` | 3+ neue Vet-Views |
| `views/visitor/*.tsx` | 2+ neue Visitor-Views |
| `components/map/*.tsx` | NEU — Zoo-Map Komponenten |
| `components/charts/*.tsx` | NEU — Diagramm-Komponenten |
| `styles.css` | Map-Styling, neue Komponenten-Styling |
| `package.json` | react-router-dom, recharts hinzufügen |

---

*Ende der Dokumentation*
