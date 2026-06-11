# Requirements und Compliance-Matrix

## Funktionale Anforderungen

| ID | Anforderung | Umsetzung | Nachweis |
| --- | --- | --- | --- |
| FR-01 | Login | `POST /auth/login` akzeptiert JSON, prueft Passwort-Hash und aktive Nutzer | `test_login_and_dashboard`, `test_login_rejects_wrong_password`, `test_login_rejects_inactive_user` |
| FR-02 | Logout | `POST /auth/logout` mit Audit-Eintrag | Code-Review, manueller Frontend-Test |
| FR-03 | Rollen | Enum `UserRole` und RBAC-Dependencies | Zugriffstests |
| FR-04 | Tiere anzeigen | `GET /animals` | Frontend Tierliste |
| FR-05 | Tiere anlegen | `POST /animals` fuer Admin/Keeper | `test_keeper_can_create_animal_and_audit_is_written` |
| FR-06 | Tiere bearbeiten | `PATCH /animals/{id}` mit Vet-Einschraenkung | `test_vet_can_only_update_animal_health_status` |
| FR-07 | Tiere deaktivieren | `DELETE /animals/{id}` als Soft Delete fuer Admin | Code-Review |
| FR-08 | Arten verwalten | `GET/POST /species` | Frontend Artenansicht |
| FR-09 | Gehege verwalten | `GET/POST /enclosures` | Frontend Gehegeansicht |
| FR-10 | Tiere Gehegen zuordnen | `Animal.enclosure_id` plus FK-Pruefung | API-Validierung |
| FR-11 | Fuetterungsplaene | `GET/POST /feeding-schedules` | Frontend Fuetterungen |
| FR-12 | Gesundheitsdaten | `GET/POST /health-records` fuer Admin/Vet | `test_health_records_are_restricted` |
| FR-13 | Aufgaben | `GET/POST/PATCH /tasks` | Frontend Aufgabenansicht |
| FR-14 | Dashboard | `GET /dashboard` | `test_login_and_dashboard` |
| FR-15 | Audit-Logs | `GET /audit-logs` fuer Admin | Audit-Test |

## Sicherheits- und Datenschutzanforderungen

| ID | Anforderung | Umsetzung | Nachweis |
| --- | --- | --- | --- |
| DS-01 | Datenminimierung | User-Modell speichert nur E-Mail, Anzeigename, Rolle, Hash, Status | Datenmodell-Review |
| DS-02 | Nicht oeffentlich | Geschuetzte Endpunkte nutzen httpOnly-Cookie-Sessions und CSRF-Header fuer Mutationen | Auth-Tests |
| DS-03 | Rollen begrenzen Zugriff | `require_roles(...)` im Backend | Zugriffstests |
| DS-04 | Synthetische Demo-Daten | `seed.py` nutzt `.example.test` und fiktive Namen | Seed-Review |
| DS-05 | Deaktivierungskonzept | Tiere werden per Soft Delete deaktiviert | API-Review |
| DS-06 | Audit ohne sensible Daten | `safe_details` filtert Secrets/Passwoerter/Tokens | Code-Review |
| DS-07 | Keine Secrets versionieren | `.gitignore` blockiert `.env` und `.env.*` | Repo-Review |
| SEC-01 | Passwort-Hashing | Argon2 via `pwdlib[argon2]`; `passlib` und `bcrypt` sind aus Requirements und Backend-Code entfernt | Backend Tests, `pip show pwdlib argon2-cffi`, `pip show bcrypt passlib` |
| SEC-02 | Serverseitige Zugriffskontrolle | FastAPI Dependencies pro Endpunkt | Tests |
| SEC-03 | IDOR-Reduktion | Entity-Lookups und Rollenpruefung pro Objektaktion | Tests/Review |
| SEC-04 | Injection-Schutz | SQLAlchemy ORM statt String-SQL | Code-Review |
| SEC-05 | Login-Limit | Thread-safe In-Memory Rate Limit pro E-Mail mit TTL-Cleanup | Code-Review |
| SEC-06 | Kontrollierte Fehler | Globaler 500-Handler mit serverseitigem Stacktrace-Logging und generischer Client-Antwort | Code-Review |
| SEC-07 | Restriktives CORS | Konfigurierbare Origin-Liste, lokal begrenzt | Config-Review |
| SEC-08 | Auditierbarkeit | Tabelle `audit_logs`, Schreibhelper `write_audit_log` | Audit-Test |
| SEC-09 | Abhaengigkeiten pruefbar | `requirements.txt`, `package.json`, `package-lock.json` | `pip show`, `npm audit`, Build-Kommandos |
| SEC-10 | Security dokumentiert | `docs/security-privacy.md`, `docs/threat-model.md` | Dokumentenreview |
