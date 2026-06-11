# Datenmodell v2

Alle Tabellen sind in `backend/app/models.py` definiert und ueber Alembic-Migrationen
(`backend/alembic/versions/0001`–`0007`) versioniert.

## Stammdaten & Zugang

- `users`: Login-E-Mail (unique), Anzeigename, Passwort-Hash (Argon2), Rolle, Aktivstatus, Zeitstempel
- `species`: Name (unique), wissenschaftlicher Name, Kategorie, Schutzstatus, Haltungsnotizen
- `enclosures`: Name (unique), Standort, Kapazitaet (>= 0), Sicherheitsstatus, Notizen, Kartenfelder (`map_*`), oeffentliche Anzeigedaten
- `animals`: Name, Art, Gehege, Geburtsdatum, Geschlecht, Gesundheitsstatus, Aktivstatus (Soft-Delete), Zeitstempel

## Pflege & Betrieb

- `feeding_schedules`: Tier, Futtertyp, Menge, Uhrzeit, Intervall, verantwortliche Rolle, Notizen
- `health_records`: Tier, erfassender Nutzer, Typ, Beschreibung, Medikation, naechste Kontrolle
- `tasks`: Titel, Beschreibung, Typ, Rolle, Faelligkeit, Status, optionale Tier-/Gehege-Referenz
- `care_tasks`: Pflegeaufgabe fuer Keeper – Tier/Gehege, zugewiesener Keeper, Typ, Faelligkeit, Status, Abschlusszeit
- `animal_condition_reports`: Zustandsbericht des Keepers – Stimmung, Appetit, Bewegung, sichtbare Verletzungen, Vet-Check-Flag
- `vet_tasks`: Tieraerztliche Aufgabe – Tier, zugewiesener Vet, Prioritaet, Faelligkeit, Status
- `medical_reports`: Befund des Vets – Diagnose, Behandlung, Medikation, Nachsorge

## Zuweisungen

- `animal_assignments`: Tier ↔ Nutzer (Keeper/Vet), Rolle, aktiv-Flag, zugewiesen von
- `enclosure_assignments`: Gehege ↔ Nutzer (Keeper/Vet), aktiv-Flag, zugewiesen von

## Besucher, Wirtschaft & Futteroptimierung

- `map_paths`: Wegverbindung zwischen zwei Gehegen (unique je Richtung, keine Selbstkante), Distanz, Gehzeit, SVG
- `visitor_stats`: Tagesdatum, Besucherzahl (>= 0), Ticketeinnahmen (>= 0)
- `work_sessions`: Login-/Logout-Zeitpunkt und Dauer pro Nutzer (Grundlage der Lohnsimulation)
- `salary_profiles`: Stundenlohn (>= 0), optionales Monatsgrundgehalt, Steuersatz (0–100 %), aktiv-Flag (1:1 zu `users`)
- `food_items`: Futtermittel (Name unique), Einheit, Kosten/Naehrwerte je Einheit (>= 0), Bestand
- `animal_nutrition_requirements`: Naehrstoffbedarf je Art (unique je Art), Mindestkalorien/-protein, max. Fett
- `feeding_plans`: Ergebnis der Futteroptimierung – Tier, Futtermittel, Menge, Datum, Optimiert-Flag

## Audit

- `audit_logs`: Nutzerreferenz, Aktion, Entitaet, Zeitpunkt, IP-Hash (HMAC), reduzierte Details

## Beziehungen (Auszug)

- Ein Tier gehoert genau zu einer Art und einem Gehege; das Loeschen eines Tiers erfolgt als Soft-Delete (`active = false`).
- Eine Art bzw. ein Gehege kann nur geloescht werden, wenn keine Tiere mehr darauf verweisen (409 Conflict).
- Ein Zustandsbericht mit `needs_vet_check` erzeugt nur dann einen VetTask, wenn dem Tier ein aktiver Vet zugewiesen ist; andernfalls wird die Aktion abgelehnt.
- Audit-Logs koennen einem Nutzer zugeordnet sein, speichern aber keine Passwoerter, Tokens oder E-Mail-Adressen.

## Integritaet

- Eindeutigkeit: `users.email`, `species.common_name`, `enclosures.name`, `food_items.name`,
  `map_paths(from, to)`, `animal_nutrition_requirements.species_id`, `salary_profiles.user_id`.
- Wertebereiche werden ueber CHECK-Constraints erzwungen (Kapazitaeten, Mengen, Naehrwerte, Steuersatz).
- NOT-NULL-Spalten mit Default besitzen seit Migration `0007` einen `server_default`, sodass auch direkte SQL-Inserts konsistent sind.
