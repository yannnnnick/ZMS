# Rollen- und Berechtigungsmodell

| Funktion | Admin | Keeper | Vet | Viewer |
| --- | --- | --- | --- | --- |
| Login/Dashboard | Ja | Ja | Ja | Ja |
| Tiere sehen | Ja | Ja | Ja | Ja |
| Tiere anlegen | Ja | Ja | Nein | Nein |
| Tiere bearbeiten | Ja | Ja | Gesundheitsstatus | Nein |
| Tiere deaktivieren | Ja | Nein | Nein | Nein |
| Arten verwalten | Ja | Nein | Nein | Nein |
| Gehege sehen | Ja | Ja | Ja | Ja |
| Gehege verwalten | Ja | Nein | Nein | Nein |
| Fuetterungsplaene sehen | Ja | Ja | Ja | Nein |
| Fuetterungsplaene bearbeiten | Ja | Ja | Nein | Nein |
| Gesundheitsdaten sehen | Ja | Nein | Ja | Nein |
| Gesundheitsdaten anlegen | Ja | Nein | Ja | Nein |
| Aufgaben sehen | Ja | Ja | Ja | Ja |
| Aufgaben bearbeiten | Ja | Ja | Ja | Nein |
| Audit-Logs sehen | Ja | Nein | Nein | Nein |

Die Durchsetzung erfolgt im Backend. Das Frontend blendet unzulaessige Aktionen aus, ist aber nicht die Sicherheitsgrenze.

