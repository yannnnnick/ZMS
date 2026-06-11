# Zoo Management Tool — Agent Guide

## Projektübersicht

Das Zoo Management Tool ist ein webbasierter Uni-MVP zur Verwaltung von Zooprozessen. Es verwaltet Tiere, Arten, Gehege, Fütterungspläne, Gesundheits- und Pflegeeinträge, Aufgaben sowie Audit-Logs. Die Anwendung besteht aus einem Python-Backend (FastAPI) und einem React-Frontend (TypeScript/Vite). Alle Demo-Daten sind synthetisch.

## Technologie-Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2.0 (ORM), Alembic (Migrationen), Pydantic v2, PyJWT
- **Passwort-Hashing**: Argon2 über `pwdlib[argon2]` (bcrypt/passlib werden nicht mehr verwendet)
- **Datenbank**: SQLite für lokale Entwicklung; PostgreSQL optional über Umgebungsvariable `DATABASE_URL`
- **Frontend**: React 19, TypeScript 5.9, Vite 7
- **Tests**: pytest (Backend), TypeScript-Build und `npm audit` (Frontend)

## Projektstruktur

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI-App mit allen Endpunkten
│   │   ├── models.py        # SQLAlchemy-ORM-Modelle
│   │   ├── schemas.py       # Pydantic-Request/Response-Modelle
│   │   ├── security.py      # Auth, RBAC, Audit-Logging, Rate-Limiting
│   │   ├── database.py      # Engine, Session, Base, init_db
│   │   └── seed.py          # Demo-Daten
│   ├── tests/
│   │   ├── conftest.py      # Pfad-Konfiguration für Imports
│   │   └── test_api.py      # pytest-Testfälle
│   ├── alembic/
│   │   ├── env.py           # Alembic-Umgebung
│   │   └── versions/        # Migrationsskripte
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Hauptkomponente mit allen Views
│   │   ├── api.ts           # API-Client (fetch-basiert)
│   │   ├── types.ts         # TypeScript-Typdefinitionen
│   │   ├── main.tsx         # Entry Point
│   │   └── styles.css       # UI-Styling
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── docs/                    # Projektdokumentation (Scope, RBAC, Security, ...)
```

## Lokaler Start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- API-Dokumentation: `http://127.0.0.1:8000/docs`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

- UI: `http://127.0.0.1:5173`
- Falls das Backend auf einer anderen URL läuft: `VITE_API_URL` setzen (z. B. `http://127.0.0.1:8000`)

## Build und Test

### Backend-Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall app tests
```

### Frontend-Build

```powershell
cd frontend
npm install
npm run build
npm audit --audit-level=low
```

## Migrationen

SQLite lokal:

```powershell
cd backend
alembic upgrade head
```

PostgreSQL über `DATABASE_URL`:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/zoo"
```

## Architektur

### Backend

- **Monolithische FastAPI-App** mit einem zentralen `create_app()`-Factory-Pattern.
- **Datenbankzugriff**: SQLAlchemy-Sessions über `get_db()`-Dependency Injection.
- **Authentifizierung**: JWT-Token (HS256), ausgegeben bei `/auth/login`, überprüft via `OAuth2PasswordBearer`.
- **Autorisierung**: Rollenbasierte Zugriffskontrolle (RBAC) mit vier Rollen: `admin`, `keeper`, `vet`, `viewer`.
  - `get_current_user` validiert das Token.
  - `require_roles(...)` schränkt Endpunkte auf bestimmte Rollen ein.
  - Beispiel: `vet` darf bei Tieren nur den `health_status` ändern.
- **Audit-Logging**: Jede relevante Mutation (Create, Update, Delete) wird in `AuditLog` geschrieben, inkl. gehashte Client-IP. Sensitive Felder (`password`, `token`, etc.) werden vor dem Speichern herausgefiltert.
- **Rate-Limiting**: Login-Endpunkt hat ein In-Memory-Rate-Limit (max. 5 Fehlversuche in 5 Minuten pro Identifier).
- **Soft-Delete**: Tiere werden nicht physisch gelöscht, sondern auf `active = False` gesetzt.
- **Fehlerbehandlung**: Ein globaler `Exception`-Handler gibt bei unerwarteten Fehlern einen generischen 500-Response zurück (keine internen Details preisgeben).
- **CORS**: Konfiguriert für lokale Entwicklung (`http://127.0.0.1:5173`, `http://localhost:5173`), steuerbar über `CORS_ORIGINS`.

### Frontend

- **Single-Page-App** mit einem zentralen `App`-Komponenten, das je nach View unterschiedliche UI-Bereiche rendert.
- **Session-Management**: Das Backend setzt ein httpOnly JWT-Cookie und ein separates CSRF-Cookie; das Frontend speichert keine JWTs im `localStorage`.
- **API-Kommunikation**: Zentraler `api`-Client in `api.ts`, der `fetch` mit `credentials: "include"`, Timeouts und CSRF-Headern fuer Mutationen nutzt.
- **RBAC im UI**: Navigationseinträge werden basierend auf der Benutzerrolle ein-/ausgeblendet. Die Sicherheitsgrenze ist aber das Backend.

## Code-Richtlinien

- **Sprache im Code**: Englisch (Variablen, Funktionen, Klassen, Kommentare).
- **Sprache im UI und Dokumentation**: Deutsch.
- **Python**: `from __future__ import annotations` am Dateianfang, Type Hints (PEP 484), moderne SQLAlchemy 2.0-Syntax (`Mapped`, `mapped_column`).
- **TypeScript**: Strikter Modus (`strict: true`), React-JSX-Transform.
- **Keine Secrets ins Repository**: `.env`-Dateien sind in `.gitignore` ausgeschlossen. `JWT_SECRET` muss explizit gesetzt werden; `DATABASE_URL` hat nur fuer lokale Entwicklung einen SQLite-Fallback.

## Wichtige Umgebungsvariablen

| Variable | Standardwert | Beschreibung |
|----------|--------------|--------------|
| `DATABASE_URL` | `sqlite:///./zoo.db` | Datenbankverbindung |
| `JWT_SECRET` | kein Default | JWT-Signing-Secret, mindestens 32 Byte |
| `JWT_EXPIRE_MINUTES` | `30` | Token-Gültigkeit in Minuten |
| `AUTH_COOKIE_SECURE` | `true` | Secure-Flag fuer Auth- und CSRF-Cookies |
| `CORS_ORIGINS` | `http://127.0.0.1:5173,http://localhost:5173` | CORS-Whitelist |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend-URL für das Frontend |

## Demo-Zugänge

| Rolle | E-Mail | Passwort |
|-------|--------|----------|
| Admin | `admin@example.test` | `Admin12345!` |
| Keeper | `keeper@example.test` | `Keeper12345!` |
| Vet | `vet@example.test` | `Vet123456!` |
| Viewer | `viewer@example.test` | `Viewer12345!` |

## Sicherheitsaspekte

- Passwörter werden niemals im Klartext gespeichert.
- Argon2 wird für Passwort-Hashing verwendet.
- JWT-Secret und Datenbank-URL müssen in Produktion über Umgebungsvariablen gesetzt werden.
- Audit-Logs erfassen relevante Aktionen, aber keine Passwörter oder Tokens.
- Client-IPs werden für Audit-Logs gehasht (SHA-256, auf 24 Zeichen gekürzt).
- Das Frontend ist keine Sicherheitsgrenze — alle Berechtigungen werden serverseitig geprüft.
