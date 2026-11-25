# Mitglieder importieren

Unter **Mitgliederimport** können Verwaltende neue Mitglieder aus einer CSV- oder
Excel-Datei (`.xlsx`, erstes Tabellenblatt) übernehmen.

1. Die Vorlage herunterladen und die Beispielzeile durch die eigenen Daten ersetzen.
   `Nr` und `Mailadresse` sind erforderlich. Spaltennamen nicht umbenennen.
2. Abholorte und gegebenenfalls Vereinsmitgliedschaftstypen vorher in Tapir anlegen.
3. Die Datei auswählen und **Datei prüfen** anklicken. Die Vorschau speichert nichts.
   Fehler werden mit der Zeilennummer angezeigt; bitte in der Quelldatei korrigieren
   und diese erneut hochladen.
4. Mit **Mitglieder importieren** die geprüfte Datei übernehmen. Bei einem Fehler
   wird nichts aus der Datei gespeichert. Die Prüfung ist eine Stunde gültig.

Bereits vorhandene Mitgliedsnummern werden übersprungen; bestehende Mitglieder
werden nicht geändert. Bereits vorhandene Benutzerkonten ohne Mitgliedschaft
können in diesem ersten Schritt noch nicht zugeordnet werden; die Prüfung zeigt
dafür einen Zeilenfehler. Fehlende SEPA- oder Datenschutzeinwilligungsdaten bleiben
unbekannt. Nur tatsächlich dokumentierte Einwilligungsdaten eintragen.

Dieser Import übernimmt keine Ernteanteilverträge oder Genossenschaftsanteile und
versendet keine Aktivierungsmails.
