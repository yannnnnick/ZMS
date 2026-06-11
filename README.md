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
python -m pip install -r requirements.txt        # Produktionsabhaengigkeiten
python -m pip install -r requirements-dev.txt     # zusaetzlich fuer Tests
$env:JWT_SECRET = "<mindestens-32-byte-zufaelliger-wert>"
$env:AUTH_COOKIE_SECURE = "false"  # nur fuer lokale HTTP-Entwicklung
python -m uvicorn app.main:app --reload
```

Eine vollstaendige Liste aller Umgebungsvariablen liegt als Vorlage unter
[`.env.example`](.env.example) im Projektwurzelverzeichnis.

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

## Frontend-Build und -Tests

```powershell
cd frontend
npm install
npm run build
npm run test          # Vitest (jsdom + Testing Library)
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

Eine vollstaendige, interaktive Referenz steht unter `http://127.0.0.1:8000/docs` bereit.

### Authentifizierung & Profil
- `POST /auth/login`, `POST /auth/logout`
- `GET /me`
- `GET /dashboard`

### Stammdaten
- `GET/POST /animals`, `GET/PATCH/DELETE /animals/{id}`
- `GET/POST /species`, `PATCH/DELETE /species/{id}`
- `GET/POST /enclosures`, `PATCH/DELETE /enclosures/{id}`
- `GET/POST /feeding-schedules`, `PATCH/DELETE /feeding-schedules/{id}`
- `GET/POST /health-records`, `PATCH/DELETE /health-records/{id}`

### Aufgaben & Pflege
- `GET/POST /tasks`, `PATCH/DELETE /tasks/{id}`
- `GET/POST /care-tasks`, `PATCH /care-tasks/{id}`
- `GET/POST /condition-reports`
- `GET/POST /vet-tasks`, `PATCH /vet-tasks/{id}`
- `GET/POST /medical-reports`

### Zuweisungen
- `GET/POST /assignments/animals`
- `GET/POST /assignments/enclosures`
- `GET /users`

### Wirtschaft & Admin
- `GET /admin/economy`
- `POST /admin/salary-simulation`
- `POST /admin/feeding-optimization`
- `GET /audit-logs`

### Oeffentlich (ohne Login)
- `GET /public/map` (ratenbegrenzt)
- `GET /health`

Die Endpunkte sind serverseitig per RBAC abgesichert; eine Detailmatrix steht in
[`docs/roles-permissions.md`](docs/roles-permissions.md).
`POST /auth/login` erwartet JSON im Format `{"email":"admin@example.test","password":"Admin12345!"}`. Die API setzt ein httpOnly-Session-Cookie und liefert `role`, `display_name` und `csrf_token`; Mutationen senden den CSRF-Wert im Header `X-CSRF-Token`.

Passwoerter werden nicht im Klartext gespeichert. Das Backend verwendet Argon2 ueber `pwdlib`; bcrypt/passlib werden nicht mehr benoetigt.
