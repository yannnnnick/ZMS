# Rollen- und Berechtigungsmodell

Die folgende Matrix spiegelt die tatsaechlich im Backend durchgesetzten
`require_roles`-Dekoratoren und Sichtbarkeitsfilter wider (`backend/app/main.py`).
Keeper und Vet sehen ausschliesslich die ihnen zugewiesenen Tiere/Gehege.

| Funktion | Admin | Keeper | Vet | Viewer |
| --- | --- | --- | --- | --- |
| Login | Ja | Ja | Ja | Ja |
| Dashboard | Ja | Ja | Ja | Nein |
| Tiere sehen (eigene Zuweisung) | Ja (alle) | Ja | Ja | Nein |
| Tiere anlegen | Ja | Ja | Nein | Nein |
| Tiere bearbeiten | Ja | Ja | nur Gesundheitsstatus | Nein |
| Tiere archivieren (Soft-Delete) | Ja | Nein | Nein | Nein |
| Arten sehen | Ja | Ja | Ja | Nein |
| Arten anlegen/bearbeiten/loeschen | Ja | Nein | Nein | Nein |
| Gehege sehen | Ja (alle) | Ja | Ja | Nein |
| Gehege anlegen/bearbeiten/loeschen | Ja | Nein | Nein | Nein |
| Fuetterungsplaene sehen | Ja | Ja | Ja | Nein |
| Fuetterungsplaene anlegen/bearbeiten/loeschen | Ja | Ja | Nein | Nein |
| Gesundheitsdaten sehen | Ja | Nein | Ja | Nein |
| Gesundheitsdaten anlegen/bearbeiten | Ja | Nein | Ja | Nein |
| Gesundheitsdaten loeschen | Ja | Nein | Nein | Nein |
| Aufgaben sehen/anlegen/bearbeiten | Ja | Ja (eigene Rolle) | Ja (eigene Rolle) | Nein |
| Pflegekalender (CareTasks) | Ja | Ja | Nein | Nein |
| Zustandsberichte anlegen | Ja | Ja | Nein | Nein |
| Vet-Kalender (VetTasks) | Ja | Nein | Ja | Nein |
| Befunde (MedicalReports) | Ja | Nein | Ja | Nein |
| Zuweisungen verwalten | Ja | Nein | Nein | Nein |
| Wirtschaft / Lohnsimulation / Futteroptimierung | Ja | Nein | Nein | Nein |
| Audit-Logs sehen | Ja | Nein | Nein | Nein |
| Oeffentliche Besucherkarte | Ja | Ja | Ja | Ja (ohne Login) |

Die Besucherkarte (`GET /public/map`) ist der einzige Einstieg fuer die Viewer-Rolle
und benoetigt keine Authentifizierung; sie ist zusaetzlich ratenbegrenzt.

Die Durchsetzung erfolgt im Backend. Das Frontend blendet unzulaessige Aktionen aus,
ist aber nicht die Sicherheitsgrenze: jeder API-Endpunkt prueft Rolle und Zuweisung serverseitig.
