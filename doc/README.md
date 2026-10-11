# Dokumentation

Einstiegspunkt für Administrator:innen und Betreiber:innen einer Tapir-Instanz.

## Betrieb & Verwaltung (Deutsch)

| Dokument | Inhalt |
|---|---|
| [email_administration.md](email_administration.md) | Welche Mails Tapir versendet, die drei getrennten Versandwege (Django/tapir-mail, Bounce-IMAP, Keycloak), Vorlagen und Fehlersuche |
| [import_users.md](import_users.md) | Testdaten entfernen, Stammdaten anlegen, Mitglieder/Anteile/Verträge per CSV importieren, Kontoaktivierung |
| [members_sample.xlsx](members_sample.xlsx) | Beispieldatei für den Mitglieder-Import |

Installation, lokale Entwicklungsumgebung und Testbefehle stehen in der [README.md](../README.md).

## Entwicklerdokumentation (Englisch)

Die technische Dokumentation ist bewusst auf Englisch, weil Code, API-Clients und die Agent-Dateien
([AGENTS.md](../AGENTS.md)) englisch sind. Sie wird nicht auf Deutsch gespiegelt — damit es nur eine Quelle gibt, die
gepflegt werden muss.

| Dokument | Inhalt | Relevant für Betrieb, wenn … |
|---|---|---|
| [dev/README.md](dev/README.md) | Überblick, Technologiestack, Einstieg für neue Entwickler:innen | … man verstehen will, wie die Teile zusammenspielen |
| [dev/architecture.md](dev/architecture.md) | Backend-Schichten, Keycloak-Berechtigungen, Hintergrundjobs, Audit-Log | … Rollen/Rechte in Keycloak vergeben oder Celery-Jobs beobachtet werden |
| [dev/frontend.md](dev/frontend.md) | React-Inseln, Vite, generierte API-Clients | … Assets nach einem Deployment fehlen |
| [dev/domain-model.md](dev/domain-model.md) | Fachmodell: Anbauperiode, Anteile, Verträge, Kündigungsfristen, Preise | … Daten importiert oder korrigiert werden |
| [dev/testing.md](dev/testing.md) | Teststruktur und Ausführung | … ein Fehler reproduzierbar gemeldet werden soll |
| [dev/operations.md](dev/operations.md) | Einstellungen, Umgebungsvariablen, Dienste, **Deployment-Checkliste** | … eine Instanz aufgesetzt oder aktualisiert wird |
| [dev/security.md](dev/security.md) | Sicherheitskritische Bereiche, Vertrauensgrenzen, Review-Checkliste | … Zugriffsrechte, Exporte mit Personendaten oder Zahlungsdaten betroffen sind |

### Besonders wichtig für den Betrieb

- **Deployment-Checkliste**: [dev/operations.md](dev/operations.md#deployment-checklist) — `SECRET_KEY`, `ALLOWED_HOSTS`,
  HTTPS, Keycloak-Secrets, `migrate` + `parameter_definitions`, Celery **und** Celery-Beat.
- **Zwei Konfigurationsebenen**: Django-Settings (per Umgebungsvariable, Neustart nötig) gegenüber `TapirParameter`
  (zur Laufzeit in der Oberfläche änderbar) — erklärt in [dev/operations.md](dev/operations.md#settings-layering).
- **Mails**: Login-, Passwort- und Aktivierungsmails kommen von Keycloak, nicht von Tapir
  ([email_administration.md](email_administration.md)).
- **Personendaten**: Exporte (CSV/PDF) bündeln personenbezogene Daten inklusive Bankverbindung — Hinweise in
  [dev/security.md](dev/security.md).
- **Vor destruktiven Kommandos immer ein Datenbank-Backup** ([import_users.md](import_users.md)).
