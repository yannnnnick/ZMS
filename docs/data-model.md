# Datenmodell v1

## Kernentitaeten

- `users`: Login-E-Mail, Anzeigename, Passwort-Hash, Rolle, Aktivstatus, Zeitstempel
- `species`: Name, wissenschaftlicher Name, Kategorie, Schutzstatus, Haltungsnotizen
- `enclosures`: Name, Standort, Kapazitaet, Sicherheitsstatus, Notizen
- `animals`: Name, Art, Gehege, Geburtsdatum, Geschlecht, Gesundheitsstatus, Aktivstatus
- `feeding_schedules`: Tier, Futtertyp, Menge, Uhrzeit, Intervall, verantwortliche Rolle
- `health_records`: Tier, erfassender Nutzer, Typ, Beschreibung, Medikation, naechste Kontrolle
- `tasks`: Titel, Beschreibung, Typ, Rolle, Faelligkeit, Status, optionale Tier-/Gehege-Referenz
- `audit_logs`: Nutzerreferenz, Aktion, Entitaet, Zeitpunkt, IP-Hash, reduzierte Details

## Beziehungen

- Ein Tier gehoert genau zu einer Art und einem Gehege.
- Ein Fuetterungsplan gehoert genau zu einem Tier.
- Ein Gesundheitseintrag gehoert genau zu einem Tier und einem erfassenden Nutzer.
- Eine Aufgabe kann optional auf ein Tier oder Gehege verweisen.
- Audit-Logs koennen einem Nutzer zugeordnet sein, speichern aber keine Passwoerter oder Tokens.

