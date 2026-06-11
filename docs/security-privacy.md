# Datenschutz- und Sicherheitskonzept

## Datenschutz

Das MVP verarbeitet nur notwendige personenbezogene oder potenziell personenbezogene Daten: Login-E-Mail, Anzeigename, Rolle, Passwort-Hash, Nutzerreferenz in Audit-Logs und Zeitpunkte von Aktionen. Demo-Daten sind synthetisch.

Nicht gespeichert werden private Adressen, Telefonnummern, Ausweisdaten, Zahlungsdaten, biometrische Daten oder echte menschliche Gesundheitsdaten.

## Zugriffskontrolle

Alle geschuetzten API-Endpunkte verlangen eine gueltige Cookie-Session. Das JWT liegt in einem httpOnly-Cookie mit `SameSite=strict`; JavaScript liest den Token nicht. Schreibende Requests muessen zusaetzlich den CSRF-Wert aus dem nicht-httpOnly CSRF-Cookie im Header `X-CSRF-Token` mitsenden. Rollen werden serverseitig mit FastAPI-Dependencies geprueft. Das Frontend dient nur der Bedienbarkeit und ist nicht die Sicherheitsgrenze.

## Passwortspeicherung

Passwoerter werden nicht im Klartext gespeichert. Das System verwendet Argon2 ueber `pwdlib` fuer Passwort-Hashing. Dadurch werden bcrypt-spezifische 72-Byte-Grenzen und passlib/bcrypt-Kompatibilitaetsprobleme vermieden. Demo-Passwoerter sind synthetisch und nur fuer die lokale Abgabeumgebung vorgesehen. Klartextpasswoerter werden nicht in Audit-Logs geschrieben.

## Audit-Logging

Relevante Aktionen wie Login, fehlgeschlagener Login, Logout, Anlegen, Aktualisieren und Deaktivieren werden protokolliert. `safe_details` entfernt sensitive Felder wie Passwort, Token, Secret, Cookie oder Authorization und begrenzt verschachtelte Detaildaten.

## Secrets

`.env` und `.env.*` sind in `.gitignore` ausgeschlossen. Konfiguration erfolgt ueber Umgebungsvariablen, zum Beispiel `DATABASE_URL`, `JWT_SECRET`, `AUTH_COOKIE_SECURE` und `CORS_ORIGINS`. `JWT_SECRET` hat keinen Code-Default mehr und muss beim Start mindestens 32 Byte lang gesetzt sein.

## Grenzen des MVP

Das Login-Rate-Limit ist als thread-safe In-Memory-Sliding-Window mit TTL-Cleanup und Kapazitaetsgrenze umgesetzt. Fuer Multi-Worker- oder Multi-Node-Deployments sollte ein persistenter Store wie Redis verwendet werden, weil Prozessspeicher nicht workeruebergreifend geteilt wird.
