# Teilmonate und Joker-Gutschriften

Wenn ein Vertrag nicht den ganzen Monat läuft, zum Beispiel bei Vertragsbeginn,
Vertragsende oder einer Vertragsänderung, zahlt das Mitglied für diesen Monat
nur einen Teil des Monatspreises. Ein Joker wird nach derselben Regel
gutgeschrieben.

Wie gerechnet wird, hängt vom Parameter "Start-Datum für anteilige Abrechnung
von Teilmonaten" ab (Konfiguration, Kategorie "Zahlungen"). Ab diesem Monat
gilt die anteilige Abrechnung nach Lieferterminen, für Monate davor die alte
Regel.

## Anteilige Abrechnung nach Lieferterminen

Ein Teilmonat kostet:

> Monatspreis × Liefertermine des Vertrags im Monat ÷ alle Liefertermine des Monats

Gezählt werden die Liefertermine des Produkttyps am Abholort des Mitglieds.

Beispiel Oktober 2026, Lieferung donnerstags (1., 8., 15., 22. und 29.):
Ein Mitglied hat bis zum 26.10. zwei mittlere Kisten à 95 €, ab dem 27.10. eine
mittlere Kiste à 95 € und eine kleine Kiste à 65 €.

- 2 mittlere Kisten: 190 € × 4 ÷ 5 = 152,00 €
- mittlere Kiste: 95 € × 1 ÷ 5 = 19,00 €
- kleine Kiste: 65 € × 1 ÷ 5 = 13,00 €
- Summe: 184,00 €

Besonderheiten:

- Wochen ohne Lieferung zählen mit. Fallen im Januar die ersten beiden Wochen
  aus und startet der Vertrag in der vierten Woche, zahlt das Mitglied 1/4 des
  Monatspreises, nicht 1/2. Eine kurzfristig eingetragene lieferfreie Woche
  ändert die Beträge also nicht.
- Gibt es im Monat keinen Liefertermin, kostet der Teilmonat 0 €.
- Produkttypen mit "Keine Lieferung" werden taggenau abgerechnet:
  Monatspreis × Vertragstage im Monat ÷ Tage im Monat. Der Solidarbeitrag wird
  immer taggenau abgerechnet.
- Produkttypen mit individuellen Lieferwochen werden weiterhin pro Lieferung
  abgerechnet: Preis pro Lieferung × Anzahl Anteile × Liefertermine des
  Vertrags im Monat. Ein Sonderpreis ersetzt Preis × Anteile.

## Joker-Gutschriften

Ein Joker wird mit dem Wert der ausgelassenen Lieferung gutgeschrieben:

> Monatspreis ÷ alle Liefertermine des Monats

Beispiel Kiste à 95 €, wöchentlich: Im Oktober 2026 (5 Liefertermine) ist ein
Joker 19,00 € wert, im November 2026 (4 Liefertermine) 23,75 €. Joker an allen
Lieferterminen eines Monats ergeben zusammen den Monatspreis.

Ist im Parameter "Produkttyp für Solidarbeitrag bei Jokern" ein Produkttyp
ausgewählt, wird der Solidarbeitrag genauso erstattet: monatlicher
Solidarbeitrag ÷ Liefertermine dieses Produkttyps im Monat. Ein Lieferzuschlag
der Verteilstation wird wie bisher erstattet.

## Monate vor dem Start-Datum

Für Monate vor dem Stichtag aus dem Parameter "Start-Datum für anteilige
Abrechnung von Teilmonaten" gilt die alte Regel:

- Ab einer Mindestanzahl Lieferungen im Monat (wöchentlich 4, 14-täglich 2,
  4-wöchentlich 1) wird der volle Monatspreis berechnet.
- Sonst kostet jede Lieferung Monatspreis × 12 ÷ Wochen im Jahr (× 2 bei
  14-täglicher, × 4 bei 4-wöchentlicher Lieferung).
- Ein Joker wird mit demselben Preis pro Lieferung gutgeschrieben.

Bei vierteljährlicher, halbjährlicher oder jährlicher Zahlung wird ein Zeitraum,
der über das Start-Datum geht, pro Monat abgerechnet: Monate davor nach der
alten Regel, Monate ab dem Start-Datum nach der neuen. Bereits bezahlte Monate
werden dadurch nicht nachberechnet, solange das Start-Datum nicht vor diese
Monate verlegt wird.

## Berechnung nachvollziehen

Im Profil des Mitglieds zeigt das Fenster "Zahlungen" bei jeder Zahlung für
Verträge, Solidarbeitrag und Vereinsmitgliedschaft sowie bei jeder Gutschrift
die Berechnung unter "Berechnung anzeigen". Mitglieder sehen diese Berechnung
ebenfalls, wenn sie ihre eigenen Zahlungen sehen dürfen.

Bei Zahlungen, die vor der Einführung dieser Funktion erzeugt wurden, ist keine
Berechnung gespeichert.
