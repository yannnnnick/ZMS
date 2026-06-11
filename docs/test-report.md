# Testbericht

Stand: 2026-06-11

## Ergebnisuebersicht

| Bereich | Command | Status | Ergebnis |
| --- | --- | --- | --- |
| Repository | `git status --short` | Bestanden | Git-Repository erkannt. Arbeitsbaum enthaelt die beabsichtigten Aenderungen; `frontend/tsconfig.tsbuildinfo` wurde aus dem Git-Index entfernt. |
| Backend Dependencies | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | Bestanden | Venv auf Requirements gebracht, `pwdlib 0.3.0` und `argon2-cffi 25.1.0` installiert. |
| Backend Argon2 | `.\.venv\Scripts\python.exe -m pip show pwdlib argon2-cffi` | Bestanden | `pwdlib 0.3.0`, `argon2-cffi 25.1.0`. |
| Backend Alt-Pakete | `.\.venv\Scripts\python.exe -m pip show bcrypt passlib` | Bestanden | `bcrypt` und `passlib` nicht installiert. |
| Backend Tests | `.\.venv\Scripts\python.exe -m pytest tests\test_api.py -q` | Bestanden | `19 passed`, 1 TestClient-Warnung. |
| Backend Compile | `.\.venv\Scripts\python.exe -m compileall app tests` | Bestanden | `app` und `tests` kompiliert. |
| Frontend Install | `npm install` | Bestanden | Dependencies aktuell, `found 0 vulnerabilities`. |
| Frontend Build | `npm run build` | Bestanden | TypeScript und Vite Build erfolgreich, `dist` erzeugt. |
| Frontend Audit | `npm audit --audit-level=low` | Nicht erneut ausgefuehrt | Externer Registry-Call wurde in diesem Durchlauf nicht ausgefuehrt. |
| Python Audit | `.\.venv\Scripts\python.exe -m pip_audit --version` | Nicht ausgefuehrt | `pip_audit` ist nicht installiert. |
| `.env`-Pruefung | `git status --short` und `.gitignore` | Bestanden | Keine `.env`-Datei im Git-Status; `.gitignore` enthaelt `.env` und `.env.*`. `.env`-Inhalte wurden nicht geoeffnet. |
| Argon2-Reste-Scan | `rg -n -i "bcrypt|passlib|CryptContext|72" backend ...` | Bestanden | Keine Treffer in produktivem Backend-Code oder Backend-Tests. |
| Lokaler Smoke-Test | Backend + Frontend HTTP | Bestanden | `/docs=200`, Login `200`, Dashboard `200`, Viewer-Tieranlage `403`, Frontend Root `200`. |

## Abgedeckte Backend-Szenarien

- Login mit Demo-Admin, httpOnly Auth-Cookie, CSRF-Token und Dashboardzugriff.
- Login lehnt falsches Passwort mit `401` ab.
- Login behandelt ein langes Passwort kontrolliert ohne Serverfehler.
- Direktes Hashing und Verifizieren eines langen Passworts funktioniert mit Argon2.
- Leeres Passwort wird beim Hashing kontrolliert abgelehnt.
- Unbekannte oder kaputte Passwort-Hash-Formate schlagen kontrolliert fehl.
- Login lehnt inaktiven Nutzer mit `403` ab.
- Viewer darf keine Tiere anlegen.
- Keeper darf Tiere anlegen und erzeugt Audit-Log.
- Vet darf nur den Gesundheitsstatus eines Tiers aendern.
- Gesundheitsdaten sind auf Admin/Vet begrenzt.
- CSRF-Header ist fuer Mutationen erforderlich.
- Abgelaufene und per Logout widerrufene Tokens werden abgelehnt.
- Fehlgeschlagene Login-Versuche werden auditiert.
- Soft-Delete blendet Tiere aus und entfernt aktive Fuetterungsplaene fuer das Tier.
- Viewer duerfen die Task-Liste nicht mehr abrufen.

## Smoke-Test-Details

Geprueft wurde lokal mit `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` und `npm run dev -- --host 127.0.0.1 --port 5173`.

| Check | Ergebnis |
| --- | --- |
| Backend `/docs` | `200` |
| Backend JSON-Login Admin | `200`, httpOnly Auth-Cookie und CSRF-Token vorhanden |
| Backend `/dashboard` mit Admin-Cookie | `200` |
| Backend Viewer `POST /animals` | `403` |
| Frontend `/` ueber Vite | `200` |

Ein Browser-Konsolencheck wurde nicht durchgefuehrt; der Smoke-Test ist HTTP/API-basiert.

Nach der Migration von passlib/bcrypt auf pwdlib/Argon2 wurden Backend-Tests, Compile-Check, Frontend-Build und Dependency-Checks erneut ausgefuehrt. Die lokale Demo-Datenbank `backend/zoo.db` wurde geloescht und beim Runtime-Smoke neu erzeugt, damit keine alten bcrypt-Hashes weiterverwendet werden.

## Bekannte Restrisiken

- Die aktuelle TestClient/httpx-Kombination erzeugt eine Starlette-Warnung, blockiert Tests aber nicht.
- Eine rekursive lokale DB-Dateisuche fand `backend/zoo.db`, brach danach aber wegen fehlender Berechtigung auf `.pytest_cache` ab. `backend/zoo.db` wurde als lokale Demo-DB neu erzeugt und ist durch `.gitignore` ausgeschlossen.
- `pip-audit` ist nicht installiert; es wurde kein Python-Dependency-Audit ausgefuehrt.
- JWT-Revocation und Login-Rate-Limit sind prozesslokal; fuer Multi-Worker-Betrieb sollte Redis oder ein anderer geteilter Store verwendet werden.
