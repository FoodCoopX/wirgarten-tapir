# Produktanteile und Anteilsgrößen benennen

Tapir zeigt den Namen eines Produktanteils und den Namen einer Anteilsgröße
nie zusammen an. Die Namen müssen deshalb jeweils für sich allein
verständlich sein.

## Empfohlene Benennung

| Was | Beispiel | Wird angezeigt |
|---|---|---|
| Produktanteil | Gemüseanteil | Als Überschrift: Auswahl der Produktanteile und Schritte im Bestellwizard, Vertragskachel im Mitgliederprofil, Abholort-Kapazitäten, Mail-Segmente |
| Anteilsgröße | S-Gemüseanteil, kleiner Gemüseanteil | Überall, wo ein Vertrag aufgelistet wird: Warenkorb und Zusammenfassung im Bestellwizard, Verträge, Lieferungen und Kündigung im Mitgliederprofil, Mails, Verwendungszweck der Lastschrift, Joker-Gutschriften |

Beispiele, wie die Namen erscheinen:

- Mail-Token "Vertragsliste": `2 × S-Gemüseanteil (01.01.2027 - 31.12.2027)`
- Mail-Token "Ernteanteilsgrößen": `1 × S-Gemüseanteil + 2 × M-Gemüseanteil`
- Verwendungszweck der Lastschrift: `2×S-Gemüseanteil`
- Kündigung im Mitgliederprofil: `S-Gemüseanteil zum 31.12.2027`

Eine Anteilsgröße, die nur "S" heißt, erscheint in Mails als `2 × S`.

## Regeln

- Produktanteile im Singular benennen ("Gemüseanteil", nicht
  "Gemüseanteile"). Manche Texte setzen den Namen in einen Satz ein, z.B.
  "Bitte wähle mindestens einen Gemüseanteil!".
- Jede Anteilsgröße braucht einen eindeutigen Namen, auch über verschiedene
  Produktanteile hinweg. Gelöschte Anteilsgrößen zählen nicht.
- Jeder Produktanteil braucht einen eindeutigen Namen.

## Umbenennen

Produktanteile und Anteilsgrößen können jederzeit umbenannt werden. Bestehende
Verträge und Zahlungen bleiben erhalten. Neue Mails und Lastschriften
verwenden ab dann den neuen Namen.
