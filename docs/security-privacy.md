# Datenschutz- und Sicherheitskonzept

## Datenschutz

Das MVP verarbeitet nur notwendige personenbezogene oder potenziell personenbezogene Daten: Login-E-Mail, Anzeigename, Rolle, Passwort-Hash, Nutzerreferenz in Audit-Logs und Zeitpunkte von Aktionen. Demo-Daten sind synthetisch.

Nicht gespeichert werden private Adressen, Telefonnummern, Ausweisdaten, Zahlungsdaten, biometrische Daten oder echte menschliche Gesundheitsdaten.

## Zugriffskontrolle

Alle geschuetzten API-Endpunkte verlangen einen gueltigen Bearer-Token. Rollen werden serverseitig mit FastAPI-Dependencies geprueft. Das Frontend dient nur der Bedienbarkeit und ist nicht die Sicherheitsgrenze.

## Passwortspeicherung

Passwoerter werden mit bcrypt ueber `passlib` gehasht. Klartextpasswoerter werden nicht gespeichert und nicht in Audit-Logs geschrieben.

## Audit-Logging

Relevante Aktionen wie Login, Logout, Anlegen, Aktualisieren und Deaktivieren werden protokolliert. `safe_details` entfernt sensitive Felder wie Passwort, Token, Secret, Cookie oder Authorization.

## Secrets

`.env` und `.env.*` sind in `.gitignore` ausgeschlossen. Konfiguration erfolgt ueber Umgebungsvariablen, zum Beispiel `DATABASE_URL`, `JWT_SECRET` und `CORS_ORIGINS`.

## Grenzen des MVP

Das Login-Rate-Limit ist in-memory und fuer lokale Demo-Zwecke geeignet. Fuer produktionsnahe Setups waere ein persistenter Store wie Redis notwendig. Das Default-`JWT_SECRET` ist nur fuer lokale Entwicklung gedacht und muss ausserhalb des Repositories gesetzt werden.

