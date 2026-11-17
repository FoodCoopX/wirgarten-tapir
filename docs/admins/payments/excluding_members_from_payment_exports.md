# Mitglieder vom Zahlungsexport ausschließen

Manchmal sollen die regelmäßigen Zahlungen eines Mitglieds eine Zeit lang
nicht per Lastschrift eingezogen werden, zum Beispiel weil das Mitglied der
Organisation Geld geliehen hat und über seinen Anteil zurückgezahlt wird.
Statt seine Verträge oder seinen Solidarbeitrag zu löschen, kannst du das
Mitglied für einen bestimmten Zeitraum vom Zahlungsexport ausschließen.

Die Zahlungen werden dann nicht eingezogen, Tapir rechnet aber weiter so, als
ob sie gezahlt würden: Statistiken wie der Cashflow oder der Solidartopf
bleiben unverändert.

## Funktion aktivieren

Die Funktion ist standardmäßig ausgeschaltet. Um sie zu aktivieren, gehe zu
"Konfiguration", Kategorie "Zahlungen", und aktiviere "Mitglieder zeitweise
vom Zahlungsexport ausschließen".

## Was sich für ein ausgeschlossenes Mitglied ändert

Während eines Ausschlusszeitraums:

- Die regelmäßigen Zahlungen des Mitglieds (Verträge, Solidarbeitrag,
  Vereinsmitgliedsbeitrag, Liefergebühren) fehlen in den Lastschriftdateien:
  den CSV- und XML-Dateien des monatlichen Exports und dem allgemeinen
  CSV-Export "Alle Zahlungen für diesen Monat".
- Die ausgeschlossenen Zahlungen werden beim Export trotzdem als bezahlt
  markiert. Auf der Seite
  "Lastschrift" werden sie getrennt als "nicht eingezogen" angezeigt.
- Zahlungen für Genossenschaftsanteile werden weiterhin eingezogen.
- Alles andere bleibt gleich: Die Zahlungen werden weiterhin erzeugt, Verträge
  und Solidarbeitrag bleiben unverändert, und Statistiken (zum Beispiel der
  Solidartopf) sind nicht betroffen.

Eine Zahlung gilt als ausgeschlossen, wenn ihr Fälligkeitsdatum im Zeitraum
liegt. Bei Mitgliedern mit vierteljährlichem, halbjährlichem oder jährlichem
Zahlungsrhythmus heißt das: Eine Zahlung, die in einem ausgeschlossenen Monat
fällig ist, wird vollständig ausgeschlossen, auch wenn sie Monate außerhalb
des Zeitraums abdeckt.

!!! note
    Das Ändern oder Löschen eines Zeitraums wirkt sich nur auf zukünftige
    Exporte aus. Bereits exportierte Zahlungen werden nicht geändert. Wenn
    vergangene Zahlungen rückwirkend betroffen sein sollen, nutze die Funktion
    "Lastschriften neu erzeugen".

!!! warning
    Gutschriften werden für ausgeschlossene Mitglieder weiterhin erzeugt, zum
    Beispiel für einen Joker oder wenn ein Vertrag reduziert wird.



## Zeitraum hinzufügen, bearbeiten oder löschen

1. Öffne das Profil des Mitglieds.
2. Klicke in der Karte "Bankverbindung" auf den Bearbeiten-Button neben
   "Vom Zahlungsexport ausgeschlossen".
3. Im sich öffnenden Fenster:
    - Klicke auf "Zeitraum hinzufügen", um einen Zeitraum hinzuzufügen. Wähle
      den ersten und den letzten Monat des Ausschlusses, oder setze den Haken
      bei "Unbefristet", wenn es noch kein Ende gibt. Du kannst einen
      Kommentar hinzufügen, zum Beispiel den Grund für den Ausschluss.
    - Mit dem Bearbeiten-Button eines Zeitraums kannst du ihn ändern, zum
      Beispiel verlängern.
    - Mit dem Löschen-Button eines Zeitraums kannst du ihn entfernen.

Zeiträume umfassen immer ganze Monate: Sie beginnen am ersten Tag des ersten
Monats und enden am letzten Tag des letzten Monats. Ein Mitglied kann mehrere
Zeiträume haben, diese dürfen sich aber nicht überschneiden.

Jede Änderung wird im Protokoll unten im Profil des Mitglieds festgehalten.

## Übersicht aller ausgeschlossenen Mitglieder

Auf der Seite "Lastschrift" zeigt der Button "Ausschlüsse vom Zahlungsexport",
wie viele aktuelle und geplante Ausschlusszeiträume es gibt. Ein Klick darauf
öffnet eine Liste dieser Zeiträume mit Mitglied, Zeitraum, Kommentar und der
Angabe, ob der Zeitraum aktiv oder geplant ist. Aktiviere "Abgelaufene
Zeiträume anzeigen", um auch beendete Zeiträume zu sehen.

Um die Zeiträume eines Mitglieds zu ändern, öffne sein Profil aus dieser Liste (Klick auf die Mitgliedsnummer) und folge
den Schritten oben.

## Was das Mitglied sieht

Wenn Mitglieder ihre eigenen Zahlungen sehen können (Konfiguration
"Mitgliederbereich", "Mitglieder können deren eigene Zahlungsreihe sehen"),
ist jede ausgeschlossene Zahlung in ihrer Liste der kommenden Zahlungen mit
"Kein Einzug per Lastschrift" markiert. Admins sehen dieselbe Markierung im
Profil des Mitglieds. Das Mitglied kann die Ausschlusszeiträume selbst weder
sehen noch ändern.
