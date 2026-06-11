# Testbericht

Stand: 2026-06-11

## Ergebnisuebersicht

| Bereich | Command | Status | Ergebnis |
| --- | --- | --- | --- |
| Repository | `git status --short` | Nicht bestanden | Projektordner ist kein Git-Repository: `fatal: not a git repository`. |
| Backend Dependencies | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | Bestanden | Venv auf Requirements gebracht, `bcrypt==4.0.1` installiert. |
| Backend Pins | `.\.venv\Scripts\python.exe -m pip show bcrypt passlib` | Bestanden | `bcrypt 4.0.1`, `passlib 1.7.4`. |
| Backend Tests | `.\.venv\Scripts\python.exe -m pytest -q` | Bestanden | `8 passed`, 19 Deprecation-Warnungen. |
| Backend Compile | `.\.venv\Scripts\python.exe -m compileall app tests` | Bestanden | `app` und `tests` kompiliert. |
| Frontend Install | `npm install` | Bestanden | Dependencies installiert, `0 vulnerabilities`. |
| Frontend Types | `npm install --save-dev @types/react @types/react-dom` | Bestanden | React-Typen fuer TypeScript ergaenzt. |
| Frontend Build | `npm run build` | Bestanden | TypeScript und Vite Build erfolgreich, `dist` erzeugt. |
| Frontend Audit | `npm audit --audit-level=low` | Bestanden | `found 0 vulnerabilities`. |
| Python Audit | `.\.venv\Scripts\python.exe -m pip_audit --version` | Nicht ausgefuehrt | `pip_audit` ist nicht installiert. |
| `.env`-Suche | `Get-ChildItem ... .env` | Nicht ausgefuehrt | Sicherheitsrichtlinie hat Pfad-Enumeration abgelehnt, weil `.env`-Pfade nicht offengelegt werden sollen. `.gitignore` wurde geprueft und enthaelt `.env` sowie `.env.*`. |
| Secret-Pattern-Scan | `rg -il --hidden ...` ohne `.env`, `.venv`, `node_modules`, `dist` | Bestanden | Keine Dateitreffer fuer einfache Key/Token/Secret-Patterns. |
| Lokaler Smoke-Test | Backend + Frontend Dev-Server | Bestanden | `/docs=200`, Login `200`, Dashboard `200`, Viewer-Tieranlage `403`, Frontend Root `200`. |

## Abgedeckte Backend-Szenarien

- Login mit Demo-Admin und Dashboardzugriff.
- Login lehnt falsches Passwort mit `401` ab.
- Login lehnt ein bcrypt-ueberlanges Passwort ohne Serverfehler mit `401` ab.
- Login lehnt inaktiven Nutzer mit `403` ab.
- Viewer darf keine Tiere anlegen.
- Keeper darf Tiere anlegen und erzeugt Audit-Log.
- Vet darf nur den Gesundheitsstatus eines Tiers aendern.
- Gesundheitsdaten sind auf Admin/Vet begrenzt.

## Smoke-Test-Details

Geprueft wurde lokal mit `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` und `npm run dev -- --host 127.0.0.1 --port 5173`.

| Check | Ergebnis |
| --- | --- |
| Backend `/docs` | `200` |
| Backend JSON-Login Admin | `200`, Bearer-Token vorhanden |
| Backend `/dashboard` mit Admin-Token | `200` |
| Backend Viewer `POST /animals` | `403` |
| Frontend `/` ueber Vite | `200` |

Ein Browser-Konsolencheck wurde nicht durchgefuehrt; der Smoke-Test ist HTTP/API-basiert.

## Bekannte Restrisiken

- Der Ordner ist kein Git-Repository, dadurch ist kein Git-Diff oder Git-Statusnachweis moeglich.
- FastAPI `on_event` und die aktuelle TestClient/httpx-Kombination erzeugen Deprecation-Warnungen, blockieren Tests aber nicht.
- `.env`-Dateipfade wurden nicht enumeriert, um keine `.env`-Informationen offenzulegen.
- `pip-audit` ist nicht installiert; es wurde kein Python-Dependency-Audit ausgefuehrt.
- Logout schreibt einen Audit-Eintrag, invalidiert bestehende JWTs aber nicht serverseitig.
