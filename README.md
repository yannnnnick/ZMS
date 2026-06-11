# Zoo Management Tool

Webbasiertes Uni-MVP zur Verwaltung von Tieren, Arten, Gehegen, Fuetterungsplaenen, Gesundheitsdaten, Aufgaben und Audit-Logs.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Datenbank: SQLite fuer lokale Entwicklung, PostgreSQL optional ueber `DATABASE_URL`
- Frontend: React, TypeScript, Vite
- Tests: pytest fuer Backend, TypeScript/Vite-Build fuer Frontend
- Passwort-Hashing: Argon2 ueber `pwdlib[argon2]`

## Lokaler Start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:JWT_SECRET = "<mindestens-32-byte-zufaelliger-wert>"
$env:AUTH_COOKIE_SECURE = "false"  # nur fuer lokale HTTP-Entwicklung
python -m uvicorn app.main:app --reload
```

Die API laeuft danach unter `http://127.0.0.1:8000`.
Die interaktive API-Dokumentation ist unter `http://127.0.0.1:8000/docs` erreichbar.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Die Oberflaeche laeuft standardmaessig unter `http://127.0.0.1:5173`.
Falls das Backend auf einer anderen URL laeuft, kann `VITE_API_URL` gesetzt werden.

## Demo-Zugaenge

Alle Demo-Daten sind synthetisch.

| Rolle  | E-Mail              | Passwort   |
| ------ | ------------------- | ---------- |
| Admin  | admin@example.test  | Admin12345!  |
| Keeper | keeper@example.test | Keeper12345! |
| Vet    | vet@example.test    | Vet123456!   |
| Viewer | viewer@example.test | Viewer12345! |

## Backend-Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall app tests
```

## Frontend-Build

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

PostgreSQL kann ueber `DATABASE_URL` konfiguriert werden, zum Beispiel:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/zoo"
```

Keine Secrets gehoeren ins Repository. Lokale `.env`-Dateien sind per `.gitignore` ausgeschlossen.

## API-Uebersicht

- `POST /auth/login`
- `POST /auth/logout`
- `GET /me`
- `GET /dashboard`
- `GET/POST /animals`
- `GET/PATCH/DELETE /animals/{id}`
- `GET/POST /species`
- `GET/POST /enclosures`
- `GET/POST /feeding-schedules`
- `GET/POST /health-records`
- `GET/POST /tasks`
- `PATCH /tasks/{id}`
- `DELETE /tasks/{id}`
- `GET /audit-logs`

Die Endpunkte sind serverseitig per RBAC abgesichert.
`POST /auth/login` erwartet JSON im Format `{"email":"admin@example.test","password":"Admin12345!"}`. Die API setzt ein httpOnly-Session-Cookie und liefert `role`, `display_name` und `csrf_token`; Mutationen senden den CSRF-Wert im Header `X-CSRF-Token`.

Passwoerter werden nicht im Klartext gespeichert. Das Backend verwendet Argon2 ueber `pwdlib`; bcrypt/passlib werden nicht mehr benoetigt.
