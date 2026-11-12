# Bestehende Vereinseinlagen importieren

Nach dem Mitgliederimport kann die Verwaltung bereits eingegangene Einlagen
mit `manage.py import-data --type deposits --file einlagen.csv --dry-run` prüfen.
Für den tatsächlichen Import `--dry-run` weglassen.

Die UTF-8-CSV benötigt zwei Spalten, zum Beispiel:

```csv
Nr;Einlage Erhalten
42;200,00
```

`Nr` ist die interne Mitgliedsnummer in Tapir. Der Betrag gehört zur jüngsten
bereits begonnenen Vereinsmitgliedschaft. Bestehende Einlageneinträge werden
geschützt. Ein identischer Wiederholungsimport wird übersprungen.
Tapir speichert den eingegangenen Betrag, ohne ein SEPA-Mandat oder eine
Lastschrift anzulegen.

Optional lassen sich offene Beträge und individuelle Anfragen übernehmen:

```csv
Nr;Einlage Erhalten;Einlage Offen;Einlage Status
42;150,00;50,00;vereinbart
43;;;offen
```

Ein importierter offener Betrag bleibt zur Klärung stehen. Der Import plant
keinen Einzug. Eine offene Anfrage enthält keinen Betrag.
