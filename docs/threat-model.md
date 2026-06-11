# Threat Model

## Assets

- Zugangsdaten und Passwort-Hashes
- Rollen und Berechtigungen
- Tier-, Gehege-, Gesundheits- und Aufgabendaten
- Audit-Logs

## Angreiferannahmen

- Nicht angemeldete Nutzer versuchen API-Zugriff.
- Angemeldete Nutzer versuchen Funktionen ausserhalb ihrer Rolle.
- Nutzer manipulieren IDs in URL oder Payload.
- Fehlkonfigurationen koennen Secrets oder interne Fehler offenlegen.

## Bedrohungen und Massnahmen

| Bedrohung | Risiko | Massnahme |
| --- | --- | --- |
| Unberechtigter Zugriff | Hoch | Bearer-Token und `get_current_user` fuer geschuetzte Endpunkte |
| Broken Access Control | Hoch | `require_roles` pro schreibendem oder sensitivem Endpunkt |
| IDOR | Mittel | Objekt-Lookup plus Rollenpruefung vor Aenderungen |
| SQL Injection | Mittel | SQLAlchemy ORM und Pydantic-Validierung |
| Unsichere Passwortspeicherung | Hoch | Argon2-Hashing ueber `pwdlib`, keine Klartextspeicherung |
| Passwort-Hash-Kompatibilitaetsfehler | Mittel | Keine passlib/bcrypt-Abhaengigkeit; lange Passwoerter werden ohne bcrypt-72-Byte-Grenze getestet |
| Brute Force Login | Mittel | In-Memory Rate Limit fuer fehlgeschlagene Logins |
| Inaktive Konten bleiben nutzbar | Mittel | Login gibt fuer inaktive Nutzer `403` zurueck, Tokens werden nur fuer aktive Nutzer akzeptiert |
| Fehlende Nachvollziehbarkeit | Mittel | Audit-Logs fuer relevante Aktionen |
| Secret-Leak | Hoch | `.gitignore`, keine `.env` im Repo, Audit-Filter |
| XSS im Frontend | Mittel | React escaped Textausgabe, keine HTML-Injection |
| Zu offene CORS-Konfiguration | Mittel | Explizite lokale Origins, per env konfigurierbar |

## Restrisiken

- Das Rate-Limit ist nicht clusterfest.
- JWT-Invalidierung ist stateless; Logout erzeugt einen Audit-Eintrag, invalidiert aber bestehende Tokens nicht serverseitig.
- Dependency-Scans muessen in der Zielumgebung ausgefuehrt werden.
- Die dokumentierte `.env`-Suche wurde nicht ausgefuehrt, weil `.env`-Pfade nicht offengelegt werden sollen; `.gitignore` schliesst `.env` und `.env.*` aus.
