# Mitglieder löschen & importieren (Admin-Doku)

Diese Anleitung beschreibt, wie man eine mit Beispieldaten befüllte Tapir-Instanz für den
Produktivbetrieb vorbereitet: bestehende (Test-)Mitglieder vollständig entfernen und eigene
Mitglieder-, Anteils- und Vertragsdaten per CSV importieren.

> **Warnung:** Alle hier beschriebenen Lösch-Kommandos sind nicht rückgängig zu machen.
> Vor jedem Schritt auf einer produktiven Datenbank ein **Datenbank-Backup** anlegen
> (siehe [Backup](#backup)).

---

## Inhalt

1. [Überblick & Reihenfolge](#1-überblick--reihenfolge)
2. [Backup](#backup)
3. [Bestehende Nutzer löschen](#3-bestehende-nutzer-löschen)
4. [Stammdaten anlegen (Voraussetzung für den Import)](#4-stammdaten-anlegen-voraussetzung-für-den-import)
5. [CSV-Format](#5-csv-format)
   - [5.1 Mitglieder (`--type members`)](#51-mitglieder---type-members)
   - [5.2 Geschäftsanteile (`--type shares`)](#52-geschäftsanteile---type-shares)
   - [5.3 Verträge/Abos (`--type subscriptions`)](#53-verträgeabos---type-subscriptions)
6. [Die Beispiel-Datei `doc/members_sample.xlsx` anpassen](#6-die-beispiel-datei-docmembers_samplexlsx-anpassen)
7. [Import durchführen](#7-import-durchführen)
8. [Nach dem Import: Keycloak-Accounts & Einladungsmails](#8-nach-dem-import-keycloak-accounts--einladungsmails)
9. [Fallstricke & bekannte Bugs](#9-fallstricke--bekannte-bugs)
10. [Kommando-Referenz](#10-kommando-referenz)

---

## 1. Überblick & Reihenfolge

Der Import ist **ausschließlich CLI-basiert** – es gibt keine Import-Oberfläche im Django-Admin
oder in der Weboberfläche. Zentrales Kommando ist
[tapir/utils/management/commands/import-data.py](../tapir/utils/management/commands/import-data.py)
(Kommandoname: `import-data`, mit **Bindestrich**).

Erwartete Reihenfolge – sie ist zwingend, weil die späteren Importe auf den früheren aufbauen:

```
0. Backup
1. Stammdaten anlegen  (Abholorte, Produkte, Produkttypen, Vertragsperiode, Vereinsmitgliedschaftstypen, Parameter)
2. Alte Nutzer löschen (import-data --reset-all)
3. Admin-Account anlegen (create_admin)
4. Mitglieder importieren      (--type members)
5. Geschäftsanteile importieren (--type shares)
6. Verträge importieren         (--type subscriptions)
7. Verifizierungs-/Einladungsmails versenden (send_verify_emails)
```

Alle Kommandos laufen im `web`-Container:

```bash
docker compose exec web poetry run python manage.py <kommando> ...
```

Die CSV-Dateien müssen **im Container** erreichbar sein. Einfachster Weg: in den gemounteten
Projektordner legen (z. B. `import/`) oder hineinkopieren:

```bash
mkdir -p import
cp ~/meine_daten/members.csv import/
# oder, falls das Verzeichnis nicht gemountet ist:
docker compose cp import/members.csv web:/tmp/members.csv
```

---

## Backup

```bash
# Dump erstellen
docker compose exec -T db pg_dump -U tapir tapir > backup_$(date +%F_%H-%M).sql

# Wiederherstellen
docker compose exec -T db psql -U tapir -d tapir < backup_2026-10-10_12-00.sql
```

> DB-Name und User ggf. aus `docker-compose.yml` / `.env.local` übernehmen.

Beachte: Keycloak hat eine **eigene** Datenbank/Realm-Konfiguration. Ein reines Tapir-DB-Backup
stellt gelöschte Keycloak-Accounts nicht wieder her.

---

## 3. Bestehende Nutzer löschen

### 3.1 Alles löschen – empfohlener Weg für den Produktivstart

```bash
docker compose exec web poetry run python manage.py import-data --reset-all
```

Das Kommando löscht **alle Mitglieder** inklusive der zugehörigen Keycloak-Accounts
(über `KeycloakUserDeleteService.delete_user_if_exists`) sowie in dieser Reihenfolge:

`SolidarityContribution`, `SubscriptionChangeLogEntry`, `TransferCoopSharesLogEntry`,
`CoopShareTransaction`, `Subscription`, `Payment`, `MandateReference`, `MemberPickupLocation`,
`LogEntry`, `QuestionaireCancellationReasonResponse`, `QuestionaireTrafficSourceResponse`,
`WaitingListEntry`, `EmailChangeRequest`, `MemberCredit`, `Joker` – danach jedes `Member`-Objekt.

**Nicht** gelöscht werden: `PickupLocation`, `Product`, `ProductType`, `ProductPrice`,
`GrowingPeriod`, `AssociationMembershipType`, `TapirParameter` sowie reine `TapirUser`
(Admin-Accounts ohne `Member`-Datensatz).

> ⚠️ `--reset-all` läuft **nicht** in einer Transaktion und wird von `--dry-run` **nicht**
> abgefangen. Es gibt keine Rückfrage. Erst Backup, dann ausführen.

### 3.2 Alles löschen als Teil eines Imports

```bash
docker compose exec web poetry run python manage.py import-data \
  --type members --file /tmp/members.csv --delete-all
```

`--delete-all` führt dieselbe Löschung aus wie `--reset-all`, aber **innerhalb derselben
Transaktion wie der Import** – schlägt der Import fehl, wird auch die Löschung zurückgerollt.
Das ist die sicherere Variante, wenn man Löschen und Import in einem Rutsch machen will.

Für die anderen Typen löscht `--delete-all` nur den jeweiligen Teilbestand:

| `--type` | gelöscht wird |
|---|---|
| `members` | kompletter Mitgliederbestand (wie `--reset-all`) |
| `shares` | `TransferCoopSharesLogEntry`, `CoopShareTransaction` |
| `subscriptions` | `SubscriptionChangeLogEntry`, `Subscription`, `PaymentTransaction`/`Payment` (außer Typ Geschäftsanteile) |

### 3.3 Nur Testdaten löschen (`populate`)

```bash
docker compose exec web poetry run python manage.py populate --clear
```

[populate.py](../tapir/utils/management/commands/populate.py) → `DataGenerator.clear()` löscht
Mitglieder **nur**, wenn deren E-Mail auf `@example.com` endet. Es löscht aber **alle** Produkte,
Produkttypen, Preise, Abholorte, Vertragsperioden, Abos und Logeinträge – also auch deine
Stammdaten.

- `populate --clear` → nur aufräumen
- `populate --reset_all [--org=bakery|wirgarten|biotop|verein|l2g|mm]` → aufräumen **und** neue
  Testdaten erzeugen. **Für Produktiv nicht verwenden.**
- Auch `./scripts/reset_all_containers.sh` und `./scripts/reset_and_start_local_server.sh` rufen
  am Ende `populate --reset_all` auf → **auf Produktivsystemen nicht benutzen.**

### 3.4 Einzelnes Mitglied löschen

**Variante A – Weboberfläche (empfohlen):** In der Mitgliederliste gibt es einen Löschen-Button
(Recht `coop.manage`). Dieser räumt alle abhängigen Objekte auf und löscht auch den
Keycloak-Account ([tapir/coop/views.py](../tapir/coop/views.py), `DeleteMemberApiView`).

**Variante B – CLI:**

```bash
# Vorschau (Default ist dry-run!)
docker compose exec web poetry run python manage.py delete-data --member-no 123 --delete-complete

# Wirklich löschen
docker compose exec web poetry run python manage.py delete-data --member-no 123 --delete-complete --dry-run no
```

| Option | Wirkung |
|---|---|
| `--member-no` / `--member-email` | eines von beiden ist Pflicht |
| `--delete-shares` | nur Geschäftsanteile |
| `--delete-subscriptions` | nur Verträge |
| `--delete-complete` | Anteile + Verträge + Mandatsreferenzen + Zahlungen + Logeinträge + Mitglied |
| `--dry-run yes\|no` | **Default `yes`** (= es wird nichts geändert) |

> ⚠️ `delete-data` löscht **nicht** den Keycloak-Account. Der muss ggf. manuell in der
> Keycloak-Admin-Konsole entfernt werden. Für vollständiges Löschen daher Variante A bevorzugen.

### 3.5 Nur Verträge löschen

```bash
# Vorschau
docker compose exec web poetry run python manage.py delete_subscriptions --members '100-120, 135, 200-205'
# Ausführen
docker compose exec web poetry run python manage.py delete_subscriptions --members '100-120' --exclude 110 --yes
```

Akzeptiert Einzelnummern und Bereiche; ohne `--yes` nur Vorschau.

---

## 4. Stammdaten anlegen (Voraussetzung für den Import)

Die Importer **legen keine Stammdaten an** – sie suchen nur per Name. Fehlt ein Name, schlägt die
betroffene Zeile fehl. Vor dem Import müssen existieren:

| Objekt | Wo anlegen | Wird referenziert über CSV-Spalte |
|---|---|---|
| Abholorte (`PickupLocation`) | Weboberfläche → Abholorte / Admin | `Abholort` (Mitglieder) |
| Vertragsperiode (`GrowingPeriod`) | Weboberfläche → Vertragsperioden | implizit über `Vertragsbeginn` |
| Produkttypen (`ProductType`) + Produkte (`Product`) + Preise (`ProductPrice`) | Weboberfläche → Produktkonfiguration | `product`, `product_type` (Verträge) |
| Vereinsmitgliedschaftstypen (`AssociationMembershipType`) | Weboberfläche → Vereinsmitgliedschaften | `Vereinsmitgliedschafttyp` (Mitglieder) |
| Parameter (`TapirParameter`) | `python manage.py parameter_definitions`, danach UI | u. a. `COOP_SHARE_PRICE`, Standard-Zahlungsrhythmus |

```bash
docker compose exec web poetry run python manage.py migrate
docker compose exec web poetry run python manage.py parameter_definitions
```

### Admin-Account anlegen

Nach `--reset-all` ggf. kein Admin mehr vorhanden:

```bash
docker compose exec web poetry run python manage.py create_admin \
  --first-name Max --last-name Mustermann \
  --email admin@example.org --password 'EinSicheresPasswort'
```

Legt einen `TapirUser` mit `is_staff`/`is_superuser` an und erzeugt den passenden Keycloak-User.
Passwort anschließend ändern; nicht in Skripte/History einchecken.

---

## 5. CSV-Format

Für **alle** Dateien gilt:

| Eigenschaft | Wert |
|---|---|
| Format | **CSV** (kein Excel/XLSX – es gibt keinen XLSX-Reader im Code) |
| Trennzeichen | **Semikolon `;`** |
| Kodierung | **UTF-8** (BOM wird toleriert und entfernt) |
| Zeilenende | beliebig |
| Kopfzeile | Pflicht, erste Zeile |
| Dezimaltrennzeichen | **Punkt** (`12.50`, nicht `12,50`) |
| Datumsformat | **`JJJJ-MM-TT`** (ISO), z. B. `2025-03-01` – siehe [Fallstricke](#9-fallstricke--bekannte-bugs) |
| Leere Zeilen | werden still übersprungen |

Spaltennamen werden vor dem Abgleich normalisiert (BOM, Zero-Width-Zeichen und Word-Joiner
entfernt, geschützte Leerzeichen → normales Leerzeichen, NFKC-Normalisierung, Trim). Die
**Schreibweise inkl. Umlauten, Punkten und Leerzeichen muss ansonsten exakt** stimmen.
Zusätzliche, unbekannte Spalten werden ignoriert.

Prüfen, wie der Importer die Kopfzeile sieht:

```bash
docker compose exec web poetry run python manage.py import-data \
  --type members --file /tmp/members.csv --verify-csv
```

### 5.1 Mitglieder (`--type members`)

Importer: [tapir/utils/services/member_importer.py](../tapir/utils/services/member_importer.py).
Schlüssel ist `Nr` → `Member.member_no` (eindeutig).

| Spalte | Pflicht | Ziel / Bedeutung |
|---|---|---|
| `Nr` | **ja** | Mitgliedsnummer (ganzzahlig). Ohne Punkt! Leer/nicht-numerisch ⇒ Zeile schlägt fehl |
| `Anrede` | nein | `form_of_address` |
| `Vorname` | ja | `first_name` |
| `Nachname` | ja | `last_name` |
| `Geburtstag/Gründungsdatum` | nein | `birthdate`, ISO-Datum |
| `Straße` | nein | wird mit `Hausnr.` zu `street` zusammengesetzt |
| `Hausnr.` | nein | s. o. |
| `PLZ` | nein | `postcode` |
| `Ort` | nein | `city` |
| `Telefon` | nein | `phone_number` |
| `Telefon 2` | nein | `phone_number_landline` |
| `Mailadresse` | faktisch ja | `email` + `username`, s. u. |
| `IBAN` | nein | `iban`, Leerzeichen werden entfernt, **wird validiert** – falsche IBAN ⇒ Zeile schlägt fehl |
| `Kontoinhaber` | nein | `account_owner` |
| `consent_sepa` | **ja (Spalte muss existieren)** | `sepa_consent`; zusätzlich Stichtag für den Zahlungsrhythmus |
| `privacy_consent` | nein | `privacy_consent` |
| `Pseudonym` | nein | `pseudonym` |
| `Abholort` | nein | Name eines bestehenden `PickupLocation`. Leer ⇒ kein Abholort. Unbekannt ⇒ Fehler |
| `AO_gueltig_ab` | bei gesetztem Abholort sinnvoll | `MemberPickupLocation.valid_from` |
| `Zahlungsintervall` | nein | `Monatlich` \| `Vierteljährlich` \| `Halbjährlich` \| `Jährlich`. Leer ⇒ Parameter-Default |
| `Solidarpreis in EUR` | nein | Betrag, Default `0.0`. `0` ⇒ kein/gelöschter Solidarbeitrag |
| `Solidarpreis Start_Date` | nein | Fallback: Anlagedatum des Mitglieds |
| `Solidarpreis End_Date` | nein | Fallback: Ende der Vertragsperiode |
| `Vereinsmitgliedschafttyp` | nein | Name eines bestehenden `AssociationMembershipType` (Achtung: Schreibweise mit nur einem `s`) |
| `Vereinsmitgliedschaft Start_Date` | **ja, wenn Typ gesetzt** | sonst Fehler |
| `Vereinsmitgliedschaft End_Date` | nein | darf leer sein |

**E-Mail-Logik** (`build_mail`):

- leer ⇒ Platzhalter `team+missing_mail_katringer_<Nr>@foodcoopx.de`
- Duplikat ⇒ Suffix `+1`, `+2`, … vor dem `@`
- anschließend Normalisierung (`EmailNormaliser`)
- `username` wird auf die E-Mail gesetzt
- existiert bereits ein Keycloak-Account und ändert sich die E-Mail, wird sie in Keycloak
  nachgezogen

Nicht vom Importer befüllt: `street_2`, `country` (Default `DE`), `preferred_language`,
`withdrawal_consent`, `is_student`.

**Beispiel-Kopfzeile:**

```csv
Nr;Anrede;Vorname;Nachname;Geburtstag/Gründungsdatum;Straße;Hausnr.;PLZ;Ort;Telefon;Telefon 2;Mailadresse;IBAN;Kontoinhaber;consent_sepa;privacy_consent;Pseudonym;Abholort;AO_gueltig_ab;Zahlungsintervall;Solidarpreis in EUR;Solidarpreis Start_Date;Solidarpreis End_Date;Vereinsmitgliedschafttyp;Vereinsmitgliedschaft Start_Date;Vereinsmitgliedschaft End_Date
1;Frau;Erika;Mustermann;1980-04-12;Hauptstraße;12a;12345;Musterstadt;+49 170 1234567;;erika@example.org;DE02120300000000202051;Erika Mustermann;2024-01-15;2024-01-15;;Blumenthal G;2024-01-15;Monatlich;0;;;Fördermitgliedschaft;2024-01-15;
```

### 5.2 Geschäftsanteile (`--type shares`)

Importer: [tapir/utils/services/share_importer.py](../tapir/utils/services/share_importer.py).

| Spalte | Bedeutung |
|---|---|
| `Mitgliedsnummer` | Zuordnung über `member_no`; unbekannt ⇒ Fehler |
| `Bewegungsart (Z,Ü,K)` | `Z` = Zeichnung/Kauf, `Ü` = Übertragung (ein-/ausgehend je nach Vorzeichen der Anzahl), `K` = Kündigung. Andere Werte ⇒ Fehler |
| `Datum` | Gültigkeitsdatum (ISO) |
| `Anzahl Anteile` | ganzzahlig |
| `Wert Anteile` | wird **ignoriert** – der Preis kommt aus dem Parameter `COOP_SHARE_PRICE` |
| `Übertragungspartner` | Mitgliedsnummer der Gegenseite, nur bei `Ü` |
| `Wirkung Kündigung` | bei `K`: überschreibt `Datum` |

Duplikaterkennung über `(Mitglied, Bewegungsart, Datum, Übertragungspartner)`.
Mandatsreferenz und Zahlung werden automatisch erzeugt.

```csv
Mitgliedsnummer;Bewegungsart (Z,Ü,K);Datum;Anzahl Anteile;Wert Anteile;Übertragungspartner;Wirkung Kündigung
1;Z;2017-03-10;2;100;;
```

### 5.3 Verträge/Abos (`--type subscriptions`)

Importer: [tapir/utils/services/subscription_importer.py](../tapir/utils/services/subscription_importer.py).
Der Kommentar am Dateianfang dort ist veraltet – maßgeblich ist diese Tabelle.

| Spalte | Pflicht | Bedeutung |
|---|---|---|
| `Mitgliedernummer` | ja* | Achtung: Schreibweise mit **„er“** (anders als bei den Anteilen!) |
| `Email` | ja* | Fallback-Zuordnung, falls die Nummer nicht trifft |
| `Vertragsbeginn` | **ja** | muss in eine bestehende `GrowingPeriod` fallen |
| `Vertragsende` | **ja** | fehlt sie, schlägt die Zeile mit „Missing end date“ fehl |
| `product` | ja | Produktname |
| `product_type` | bei mehrdeutigem Produktnamen | Produkttypname |
| `Quantity` | ja | Anzahl, ganzzahlig |
| `Probezeit` | nein | wahr bei `1/true/yes/ja/j/y/x`; leer ⇒ nicht gesetzt |
| `Ende Probezeit (Sonntag)` | nein | überschreibt das Probezeitende |
| `consent_vertragsgrundsätze` | nein | Zeitstempel |
| `consent_widerruf` | nein | Zeitstempel |
| `cancellation.ts` | nein | Kündigungszeitpunkt |
| `Personalisierter Betrag` | nein | überschreibt den Produktpreis |

\* mindestens eines von `Mitgliedernummer` / `Email` muss zum Mitglied führen.

Duplikaterkennung über `(Mitglied, Produkt, Vertragsbeginn)`. Hat der Produkttyp einen
Lieferrhythmus (≠ „keine Lieferung“) und das Mitglied **keinen Abholort**, schlägt die Zeile fehl –
deshalb zwingend erst Mitglieder (mit `Abholort`) importieren.

```csv
Mitgliedernummer;Email;Vertragsbeginn;Vertragsende;product;product_type;Quantity;Probezeit;Ende Probezeit (Sonntag);consent_vertragsgrundsätze;consent_widerruf;cancellation.ts;Personalisierter Betrag
1;erika@example.org;2025-03-01;2026-02-28;M;Ernteanteile;1;ja;2025-03-30;2025-02-20;2025-02-20;;
```

---

## 6. Die Beispiel-Datei `doc/members_sample.xlsx` anpassen

Die vorhandene Datei hat 987 Datenzeilen und folgende Kopfzeile:

```
Nr. | Nachname | Vorname | Depot | Gemüse | Kartoffeln | Zitrus | Käse | Bemerkungen |
Mail 1 | Mail 2 | Telefon | Betrag insgesamt\nmonatlich | Bemerkungen Abbuchung |
IBAN | MANDAT-Referenznr. | Str. Hausnr. | PLZ Ort | Bankverbindung | Vetragdatum
```

**Dieses Format ist so nicht importierbar.** Nötige Anpassungen:

### 6.1 Spalten umbenennen

| aktuell | muss heißen |
|---|---|
| `Nr.` | `Nr` (**ohne Punkt**) |
| `Depot` | `Abholort` – und der Wert muss exakt dem Namen eines angelegten `PickupLocation` entsprechen |
| `Mail 1` | `Mailadresse` |
| `Telefon` | `Telefon` (passt bereits) |
| `IBAN` | `IBAN` (passt bereits; Format validieren!) |
| `Vorname`, `Nachname` | passen bereits |

### 6.2 Spalten aufteilen

| aktuell (kombiniert) | muss werden |
|---|---|
| `Str. Hausnr.` | `Straße` + `Hausnr.` (zwei Spalten) |
| `PLZ Ort` | `PLZ` + `Ort` (zwei Spalten) |

### 6.3 Spalten ergänzen

Fehlen aktuell komplett und sollten ergänzt werden:
`Anrede`, `Geburtstag/Gründungsdatum`, `Kontoinhaber`, `consent_sepa` (**Spalte ist Pflicht**),
`privacy_consent`, `AO_gueltig_ab`, `Zahlungsintervall`, `Solidarpreis in EUR`,
`Solidarpreis Start_Date`, `Solidarpreis End_Date`, `Vereinsmitgliedschafttyp`,
`Vereinsmitgliedschaft Start_Date`, `Vereinsmitgliedschaft End_Date`.

`Vetragdatum` [sic] ist kein Importfeld – ggf. als Quelle für `consent_sepa` verwenden.

### 6.4 Spalten in eigene Dateien auslagern

`Gemüse`, `Kartoffeln`, `Zitrus`, `Käse` sind Vertragsmengen. Sie gehören **nicht** in die
Mitglieder-CSV, sondern in eine separate Verträge-CSV im Format aus
[Abschnitt 5.3](#53-verträgeabos---type-subscriptions) – pro Produkt und Mitglied **eine Zeile**
(„unpivotieren“):

| Nr | Gemüse | Käse | → | Mitgliedernummer | product | Quantity |
|---|---|---|---|---|---|---|
| 1 | 1 | 2 | → | 1 | Gemüse | 1 |
| | | | | 1 | Käse | 2 |

`Mail 2`, `Bemerkungen`, `Bemerkungen Abbuchung`, `Betrag insgesamt monatlich`,
`MANDAT-Referenznr.`, `Bankverbindung` haben keine Entsprechung im Importer und werden ignoriert
(können in der Datei bleiben oder entfernt werden). Mandatsreferenzen erzeugt Tapir selbst.

### 6.5 Datentypen bereinigen

- Alle Datumsfelder auf **`JJJJ-MM-TT`** umstellen (in Excel: Zellformat `JJJJ-MM-TT`).
- `Solidarpreis in EUR` mit **Punkt** als Dezimaltrennzeichen.
- IBANs ohne Leerzeichen bzw. in gültigem Format – ungültige IBANs lassen die Zeile scheitern.
- Zeilen ohne Mitgliedsnummer entfernen (in der Beispieldatei gibt es Zeilen ohne Namen).
- Zeilenumbrüche in Kopfzeilen entfernen (`Betrag insgesamt\nmonatlich`).

### 6.6 Als CSV exportieren

Excel: *Datei → Speichern unter → CSV UTF-8 (durch Trennzeichen getrennt)*. Anschließend prüfen,
dass wirklich `;` als Trennzeichen verwendet wurde. LibreOffice: *Speichern unter → Text CSV →
Filtereinstellungen bearbeiten → Zeichensatz `Unicode (UTF-8)`, Feldtrenner `;`,
Zeichenketten-Trenner `"`*.

Ergebnis: bis zu drei Dateien, z. B. `members.csv`, `shares.csv`, `subscriptions.csv`.

---

## 7. Import durchführen

### Schritt 1 – Kopfzeile prüfen (keine DB-Änderung)

```bash
docker compose exec web poetry run python manage.py import-data \
  --type members --file /tmp/members.csv --verify-csv
```

Ausgabe: rohe Kopfzeile, bereinigte Kopfzeile und die erste Datenzeile als Dictionary.
Hier kontrollieren, ob alle erwarteten Spaltennamen exakt getroffen sind.

### Schritt 2 – Probelauf

```bash
docker compose exec web poetry run python manage.py import-data \
  --type members --file /tmp/members.csv --dry-run --stacktrace
```

`--dry-run` führt den kompletten Import aus und rollt die Transaktion am Ende zurück.
`--stacktrace` gibt zu jeder fehlerhaften Zeile den vollen Traceback aus (sonst nur eine
Kurzmeldung). Fehlerzeilen werden mit Zeilennummer in der Datei gemeldet.

Am Ende steht immer: `Done. Created: X, Updated: Y, Skipped: Z`.
Ziel: `Skipped: 0`.

### Schritt 3 – Echtlauf

```bash
# 1) Mitglieder
docker compose exec web poetry run python manage.py import-data \
  --type members --file /tmp/members.csv

# 2) Geschäftsanteile
docker compose exec web poetry run python manage.py import-data \
  --type shares --file /tmp/shares.csv

# 3) Verträge
docker compose exec web poetry run python manage.py import-data \
  --type subscriptions --file /tmp/subscriptions.csv
```

### Korrekturläufe

Standardmäßig werden bereits vorhandene Datensätze **übersprungen**. Um sie zu aktualisieren:

```bash
docker compose exec web poetry run python manage.py import-data \
  --type members --file /tmp/members.csv --update yes
```

Mit `--update yes` wird jedes Feld mit dem CSV-Wert abgeglichen und bei Abweichung überschrieben.
**Leere CSV-Zellen überschreiben bestehende Werte mit leer** – Korrekturdateien daher immer
vollständig halten.

Jede Zeile läuft in einer eigenen Untertransaktion: Eine fehlerhafte Zeile bricht den Lauf nicht
ab, sie wird als „skipped“ gezählt. Der Gesamtlauf liegt zusätzlich in einer äußeren Transaktion.

---

## 8. Nach dem Import: Keycloak-Accounts & Einladungsmails

Der Mitglieder-Import legt **keine** Keycloak-Accounts an. Die Mitglieder können sich also noch
nicht einloggen. Das erledigt:

```bash
# Vorschau
docker compose exec web poetry run python manage.py send_verify_emails --dry-run

# Versand
docker compose exec web poetry run python manage.py send_verify_emails
```

[send_verify_emails.py](../tapir/wirgarten/management/commands/send_verify_emails.py) versendet
Verifizierungsmails an alle Mitglieder **ohne** Keycloak-Account, die mindestens einen
Geschäftsanteil **oder** einen aktuellen/zukünftigen Vertrag haben. Mitglieder ohne beides werden
ignoriert.

Optionale Eingrenzung für gestaffelten Versand:

- `--only-members-with-subscription`
- `--only-members-without-subscription`

> Vor dem ersten Echt-Versand unbedingt prüfen, dass die E-Mail-Konfiguration korrekt ist und
> keine Platzhalteradressen (`team+missing_mail_...@foodcoopx.de`) mehr im Bestand sind.

---

## 9. Fallstricke & bekannte Bugs

1. **Nur ISO-Daten funktionieren zuverlässig.** In
   [data_import_utils.py](../tapir/utils/services/data_import_utils.py) ruft der Fallback für
   deutsche Datumsformate `datetime.date.strptime(...)` auf – diese Methode existiert nicht
   (`AttributeError`). Formate wie `15.01.2024` oder `15/01/2024` führen daher zum Fehler.
   **Immer `JJJJ-MM-TT` verwenden.**
2. **Die Spalte `consent_sepa` muss existieren.** Sie wird mit `row["consent_sepa"]` gelesen
   (nicht `.get`) – fehlt die Spalte, scheitert *jede* Zeile mit `KeyError`. Der Wert darf leer
   sein, die Spalte nicht fehlen.
3. **`Nr` ohne Punkt**, **`Mitgliedsnummer`** (Anteile) vs. **`Mitgliedernummer`** (Verträge) –
   unterschiedliche Schreibweisen, leicht zu verwechseln.
4. **`Vereinsmitgliedschafttyp`** mit nur einem `s` (nicht „-schaftstyp“).
5. **`--dry-run` schützt nicht vor `--reset-all`** – der Reset-Zweig läuft vor der Transaktion.
6. **Stammdaten werden nie angelegt**, nur per Name gesucht.
7. **Importreihenfolge** Mitglieder → Anteile → Verträge ist zwingend.
8. **Keine automatisierten Tests** für die Importer – nach dem Import stichprobenartig in der
   Oberfläche prüfen (Mitgliederliste, Anteile, Verträge, Zahlungen).
9. **IBAN wird validiert.** Testdaten mit Fantasie-IBANs scheitern.
10. **Kein XLSX-Support.** Die Excel-Datei muss immer zu CSV konvertiert werden.

### Kontrolle nach dem Import

```bash
docker compose exec web poetry run python manage.py shell -c "
from tapir.wirgarten.models import Member, Subscription, CoopShareTransaction, MemberPickupLocation
print('Mitglieder:', Member.objects.count())
print('ohne Abholort:', Member.objects.exclude(id__in=MemberPickupLocation.objects.values('member_id')).count())
print('Platzhalter-Mails:', Member.objects.filter(email__contains='missing_mail').count())
print('Anteile:', CoopShareTransaction.objects.count())
print('Vertraege:', Subscription.objects.count())
"
```

---

## 10. Kommando-Referenz

### `import-data`

```bash
python manage.py import-data [--type members|shares|subscriptions] [--file PFAD]
                             [--update yes|no] [--delete-all] [--reset-all]
                             [--dry-run] [--stacktrace] [--verify-csv]
```

| Option | Default | Wirkung |
|---|---|---|
| `--type` | – | Importer-Auswahl. Pflicht, außer bei `--reset-all` |
| `--file` | – | Pfad zur CSV **im Container**. Pflicht, außer bei `--reset-all` |
| `--update` | `no` | `no`: vorhandene Datensätze überspringen. `yes`: abgleichen und aktualisieren |
| `--delete-all` | aus | Bestand des gewählten Typs vor dem Import löschen (in derselben Transaktion) |
| `--reset-all` | aus | Alles mitgliederbezogene löschen (inkl. Keycloak) und sofort beenden |
| `--dry-run` | aus | Import ausführen und zurückrollen |
| `--stacktrace` | aus | Vollen Traceback pro Fehlerzeile ausgeben |
| `--verify-csv` | aus | Nur Kopfzeile + erste Zeile anzeigen, keine DB-Änderung |

### Weitere Kommandos

| Kommando | Zweck |
|---|---|
| `create_admin --first-name … --last-name … --email … --password …` | Admin-Account + Keycloak-User anlegen |
| `delete-data --member-no N --delete-complete --dry-run no` | Einzelnes Mitglied löschen (**ohne** Keycloak) |
| `delete_subscriptions --members '1-50' --yes` | Verträge ausgewählter Mitglieder löschen |
| `parameter_definitions` | Parameterdefinitionen in die DB schreiben |
| `populate --clear` | Testdaten entfernen (löscht auch Produkte/Abholorte!) |
| `send_verify_emails [--dry-run]` | Keycloak-Einladungen an importierte Mitglieder |
| `backfill_member_numbers` | Fehlende Mitgliedsnummern nachtragen |
| `rebuild_payment_history` | Zahlungshistorie neu aufbauen |
| `regenerate_mandate_references` | Mandatsreferenzen neu erzeugen |
