# Zusätzliche E-Mail-Adressen

Mitglieder können neben ihrer Hauptadresse weitere E-Mail-Adressen eintragen,
zum Beispiel für Mitbewohner:innen oder Partner:innen, die die Mails der
Organisation auch lesen möchten.

## Funktion aktivieren

Die Funktion ist standardmäßig ausgeschaltet. Um sie zu aktivieren, gehe zu
"Konfiguration", Kategorie "Mail", und aktiviere "Zusätzlich E-Mail-Adressen
erlauben". Den Text, den Mitglieder beim Eintragen sehen, kannst du unter
"Erklärungstext zu zusätzliche Adressen" anpassen.

Beim Ausschalten wird nichts gelöscht: Adressen, Anmeldungen und
Mailinglisten-Abos bleiben erhalten. Tapir schickt nur keine Mails mehr an
diese Adressen, und Mitglieder können sie nicht mehr verwalten. Auf
Mailinglisten bleiben die Adressen, bis ein Admin sie entfernt. Nach dem
Wiedereinschalten ist alles wie vorher.

## Eine Adresse hinzufügen

Das Mitglied trägt die Adresse in seinem Profil unter "Zusätzliche
Mail-Adressen verwalten" ein. Tapir schickt einen Bestätigungslink an die
neue Adresse. Erst nach der Bestätigung erhält die Adresse Mails.

Beim Eintragen wählt das Mitglied, ob die Adresse auch persönliche Mails
erhält:

- **Persönliche Mails**: Die Adresse bekommt eine Kopie aller Mails an die
  Hauptadresse (Verträge, Abholung, Rundmails an alle Mitglieder). Bei der
  Bestätigung übernimmt sie außerdem die Anmeldungen des Mitglieds zu
  Mail-Kategorien und Mailinglisten.
- **Nur Abos**: Die Adresse bekommt nur Mails der Kategorien und
  Mailinglisten, für die sie selbst angemeldet ist.

Die Anmeldungen werden nur bei der ersten Bestätigung übernommen. Danach sind
die Anmeldungen der Adresse unabhängig von denen des Mitglieds.

## Eine Adresse gehört genau einer Person

Eine Adresse ist entweder die Hauptadresse eines Mitglieds oder die bestätigte
zusätzliche Adresse eines Mitglieds, nie beides.

- Die Bestätigung wird abgelehnt, wenn die Adresse schon die Hauptadresse
  eines Mitglieds ist oder bei einem anderen Mitglied als zusätzliche Adresse
  bestätigt ist.
- Wird eine Adresse zur Hauptadresse eines Mitglieds (durch eine
  Adressänderung oder ein neues Mitglied), werden alle zusätzlichen Adressen
  mit dieser Adresse gelöscht.
- Eine Adresse darf zusätzlich auch als externe Empfänger:in für öffentliche
  Kategorien eingetragen sein.

## Abos verwalten

Wer eine zusätzliche Adresse besitzt, hat kein eigenes Konto. Die Abos der
Adresse werden über einen Verwaltungslink geändert:

- Das Mitglied kann den Link im Profil über "Link senden" an die Adresse
  schicken.
- Auf der öffentlichen Seite `(http://solawi.de/)core/subscription_management_link_request` kann
  jede:r den Link für eine Adresse anfordern. Er wird nur an bestätigte
  zusätzliche Adressen und externe Empfänger:innen geschickt, höchstens einmal
  alle 15 Minuten pro Adresse.
- In Mail-Vorlagen liefert das Token "Empfänger (extra).Newsletter -
  Verwaltungslink" an zusätzlichen Adressen und externen Empfänger:innen einen
  frischen Verwaltungslink, an Hauptadressen einen Link zum Mitgliederprofil.

Der Link ist 72 Stunden gültig. Danach muss ein neuer angefordert werden. Auf
der Seite kann die Adresse ihre Kategorien und Mailinglisten ändern oder die
Verbindung zum Mitglied trennen, was die zusätzliche Adresse löscht.

## Ehemalige Mitglieder

Wenn ein Mitglied die Organisation verlässt, entfernt Tapir in der Nacht seine
Hauptadresse und alle seine zusätzlichen Adressen von allen Mailinglisten.
Neue Anmeldungen zu Mailinglisten sind für diese Adressen gesperrt.
