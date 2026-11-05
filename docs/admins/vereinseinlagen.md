# Vereinseinlagen

Die rückzahlbare Vereinseinlage wird zusätzlich pro Mitglied geführt. Vereinsmitgliedschaft, separat erhobene Vereinsbeiträge und laufende Ernte-/Solidarbeiträge bleiben bestehen. Bestehende Beiträge werden nicht in Einlagen umgewandelt.

Unter **Konfiguration → Parameter** lassen sich Einlagen aktivieren, Name, Mindestbetrag und Schrittgröße festlegen sowie Einlagenpflicht für Fördermitglieder, freiwillige Erhöhungen, Standardraten und Härtefallanmeldungen einstellen. Ein erhöhter Mindestbetrag erzeugt keine Nachbelastungen. Standardraten sind monatlich; die Anzahl ist konfigurierbar. Centreste werden auf die ersten Raten verteilt, sodass die Summe genau dem vereinbarten Betrag entspricht. Zinsen und Gebühren fallen nicht an.

## Individuelle Vereinbarung

Mit der Härtefallcheckbox wird die Anmeldung fortgesetzt. Im Mitgliederprofil, im Dashboard und im Mitgliederfilter erscheint **Individuelle Vereinbarung offen**. Es gibt noch keinen vereinbarten Betrag, keine Forderung und keinen Einzug.

Für eine Verwaltungsbenachrichtigung kann im Mailmodul der optionale Auslöser **Vereinseinlage: Individuelle Vereinbarung offen (an Verwaltung)** konfiguriert und freigegeben werden. Empfänger ist die konfigurierte Admin-E-Mail-Adresse. Ohne freigegebene Mailkonfiguration bleibt der Fall weiterhin in der Verwaltungsübersicht sichtbar. Die Checkbox verspricht keine automatische Kontaktaufnahme.

Nach Abstimmung dokumentiert die Verwaltung im Mitgliederprofil über **Individuelle Vereinbarung dokumentieren** die Zustimmung des Mitglieds mit Datum und Beleg/Grund:

- **0 €:** abgeschlossene Befreiung, kein offener Einzug.
- **100 € statt 200 €:** 100 € vereinbarter Gesamtbetrag; keine zusätzliche Forderung über die Differenz.
- **200 € in vier Raten:** insgesamt 200 €, normalerweise vier monatliche Einzüge à 50 €.

Bereits erhaltene Beträge werden bei einem neuen Zahlungsplan angerechnet. Nur noch nicht exportierte Einzüge werden ersetzt. Exportierte Zahlungen bleiben erhalten. Bei Kündigung der Einlage werden offene Einzüge aufgehoben; das gebuchte Guthaben wird erst ab dem Austrittsdatum in der Rückzahlungsprüfliste berücksichtigt. Ein bloßer Wechsel des Mitgliedschaftstyps kündigt die Einlage nicht.

Bei Wiedereintritt nach einer Kündigung bleibt die gesamte Zahlungs- und Vereinbarungshistorie erhalten. Die Einlage wird wieder geöffnet, zunächst mit **Individuelle Vereinbarung offen** und ohne neue Lastschriften. Das gilt auch nach vollständiger Rückzahlung. Ein vorhandenes Guthaben ist bis zur neuen Vereinbarung kein automatisch rückzahlbarer Betrag; das zurückgekehrte Mitglied steht nicht mehr in der Austritts-Rückzahlungsübersicht. Erst eine ausdrücklich dokumentierte neue Vereinbarung legt Gesamtbetrag und Zahlungsplan fest und rechnet das verbliebene Guthaben an.

## Zahlungen und Rückzahlungen

Einzüge verwenden die vorhandenen SEPA-Mandate und den konfigurierten Einzugstag. Ein SEPA-Export ist keine Bestätigung des Bankeingangs: Tapir berücksichtigt exportierte Einzüge ab dem vorgesehenen Einzugstag im gebuchten Guthaben. Fehlerhafte Exportzeilen bleiben offen und können nach Korrektur erneut exportiert werden. Erfolgreich exportierte Zeilen werden dabei nicht erneut eingezogen.

Tatsächliche externe Zahlungseingänge, Rücklastschriften/Korrekturen und bereits ausgeführte Rückzahlungen können mit Datum und Beleg im Profil erfasst werden. Ein externer Zahlungseingang reduziert offene Einzüge. Es entsteht kein Überweisungsablauf für neue Bestellungen. Tapir führt keine ausgehenden Rückzahlungen aus.

Unter **Exporte → CSV-Vorlagen** kann die Vorlage **Vereinseinlagen: Rückzahlungsübersicht** angelegt werden. Sie erzeugt jährlich eine Prüfliste ausgeschiedener Mitglieder mit verbleibendem Guthaben und Bankdaten, einschließlich noch offener Beträge früherer Austrittsjahre. Termin und Mailversand werden über die bestehenden Export-Einstellungen verwaltet. Die Liste begründet keinen festen Auszahlungstermin; Vereinbarungen und Liquidität müssen außerhalb von Tapir geprüft werden. Nach bestätigter externer Rückzahlung verschwindet ein vollständig ausgeglichenes Guthaben aus der Prüfliste.

Im Mailmodul stehen die dynamischen Tokens **Vereinseinlage - vereinbarter Gesamtbetrag** und **Vereinseinlage - gebuchtes Guthaben** auch für Bestellbestätigung, Beitritt und Austritt zur Verfügung.

## Historischer Import

Zuerst die Mitglieder mit ihren dauerhaft unveränderten Mitgliedsnummern importieren. Danach übernimmt `import-data --type deposits --file <datei.csv>` einen Einlagenstand pro Mitglied. Die UTF-8-Datei verwendet Semikolons. Ein bereits erhaltener Anfangsbestand allein erzeugt keine Lastschrift; das bisherige Format bleibt gültig:

```csv
Buchungs-ID;Mitgliedsnummer;Betrag;Datum;Austrittsdatum
bestand-42;42;200,00;2025-03-01;
bestand-43;43;200,00;2024-03-01;2025-12-31
```

Für bestehende Vereinbarungen mit offenen Raten oder ungeklärte Härtefälle sind zusätzliche Spalten verfügbar:

```csv
Buchungs-ID;Mitgliedsnummer;Status;Betrag;Datum;Austrittsdatum;Gesamtbetrag;Offene Raten;Vereinbarung
bestand-44;44;vereinbart;50,00;2026-10-01;;200,00;2026-12-05:50,00|2027-01-05:50,00|2027-02-05:50,00;Unterschriebener Ratenplan vom 2026-10-01
bestand-45;45;haertefall;0;;;;;
bestand-46;46;bezahlt;200,00;2026-10-01;;;;
```

- **Betrag** bezeichnet ausschließlich bereits erhaltenes Geld; **Datum** dessen Eingang. Bei 0 € bleibt das Datum leer.
- **vereinbart** übernimmt einen belegten Gesamtbetrag und genau die noch offenen Einzüge. Bereits bezahlt plus offene Raten muss centgenau dem Gesamtbetrag entsprechen. Reduzierte Gesamtbeträge sind mit Beleg möglich; es entsteht keine Forderung über die Differenz zum aktuellen Mindestbetrag.
- **Offene Raten** enthält `JJJJ-MM-TT:Betrag`, mehrere Raten getrennt mit `|`, aufsteigend nach Fälligkeit. Die Termine bleiben unverändert, auch wenn eine tatsächlich noch offene Rate bereits überfällig ist. Höchstens 120 positive Raten; gültige Bankdaten und SEPA-Zustimmung sind erforderlich. Bereits extern eingereichte oder bezahlte Lastschriften dürfen hier nicht nochmals aufgeführt werden. Der spätere SEPA-Export verwendet die üblichen Einzugstermine.
- **haertefall** übernimmt einen ungeklärten Fall, ohne Gesamtbetrag, Zahlungen, automatische Befreiung oder Schuld. Er ist im Mitgliederprofil, Verwaltungsfilter und Dashboard sichtbar. Der Import verschickt keine Benachrichtigung. Eine spätere Vereinbarung wird ausdrücklich im Profil dokumentiert.
- **bezahlt** (oder leerer Status im bisherigen Format) übernimmt ausschließlich den bezahlten Anfangsbestand. Austrittsdatum ist optional; gekündigte Einlagen dürfen keinen offenen Ratenplan enthalten.

Die Buchungs-ID muss dauerhaft gleich und organisationsweit eindeutig bleiben. Ein identischer Import wird übersprungen, auch mit `--update yes` oder nach einem zwischenzeitlichen Zahlungsexport. Abweichende Angaben unter derselben ID, eine Zuordnung zu einem anderen Mitglied oder ein zweiter Anfangsbestand werden verständlich abgelehnt. Nachträgliche Korrekturen erfolgen als dokumentierte Buchungen oder neue Verwaltungsvereinbarung. Es werden keine bestehenden Konten überschrieben und keine Bestandsmitglieder automatisch nachbelastet.

Mit `--dry-run` lässt sich die Datei ohne Speicherung prüfen. Löschung der Einlagenhistorie sowie vollständiger Mitgliederreset bei vorhandenen Einlagen sind gesperrt. Die Ausgabe benennt fehlerhafte Zeilen; erfolgreiche Zeilen bleiben beim normalen Import erhalten und können gefahrlos wiederholt werden.

## Lokaler manueller Test

Für die lokale Testorganisation sind Einlagen, Standardraten und Härtefallanmeldungen aktiviert. Mindestbetrag **200 €**, Schrittgröße **50 €**, Standardzahl **vier Monatsraten**. Die bisherigen Mitglieds- und Erntebeiträge bleiben unverändert.

1. [Registrierung](http://tapir.test:8000/bestell_wizard/bestell_wizard_mobile): Produkte auswählen; im Vereinseinlagenschritt 200 € und wahlweise vier Raten prüfen. Mit einer neuen Testadresse die Härtefallcheckbox wählen und die Registrierung abschließen.
2. Als Verwaltung anmelden und [offene Vereinbarungen](http://tapir.test:8000/tapir/members?deposit_status=pending) öffnen. Das neue Mitglied auswählen und den Mitgliederbereich öffnen.
3. Im Abschnitt Vereinseinlage **Individuelle Vereinbarung dokumentieren** wählen: 0 €, 100 € oder 200 € mit vier Raten. Zustimmung dokumentieren und Beginn festlegen. Für unabhängige Varianten jeweils eine eigene Testregistrierung verwenden.
4. Im Profil Status, Gesamtbetrag und Zahlungsplan prüfen. Mit dem Mitgliedskonto dieselbe Ansicht öffnen; das Mitglied kann keine Ausnahme selbst genehmigen.
5. Über [Parameter](http://tapir.test:8000/config/parameters) und [Dashboard](http://tapir.test:8000/tapir/admin/dashboard) die Konfiguration und Übersicht prüfen. Ein tatsächlicher Zahlungsexport ist für diesen Test nicht erforderlich.
