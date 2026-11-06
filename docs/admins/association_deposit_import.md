# Vereinseinlagen importieren

Zuerst Mitglieder mit stabiler Mitgliedsnummer und passender Vereinsmitgliedschaft
importieren. Einlagen danach separat über den bestehenden Importbefehl laden:

```sh
docker compose exec -T web poetry run python manage.py import-data --type deposits --file /app/einlagen.csv --dry-run
docker compose exec -T web poetry run python manage.py import-data --type deposits --file /app/einlagen.csv
```

Der Einlagenimport ordnet ausschließlich über `Nr` zu. Er erstellt keine Mitglieder
oder Keycloak-Konten. `--delete-all` wird für Einlagen abgewiesen.

```csv
Nr;Einlage Status;Einlage Gesamt;Einlage Erhalten;Einlage Stichtag;Einlage Beginn;Einlage Ratenzahl;Einlage Offene Raten;Einlage Individuell;Einlage Anfrage;Einlage Beleg
1001;vereinbart;200;200;2026-11-05;2026-09-01;1;;nein;;Geprüfter historischer Eingang
1002;vereinbart;200;100;2026-11-05;2026-09-01;4;2026-11-20:50|2026-12-20:50;nein;;Zwei von vier Raten offen
1003;offen;;25;2026-11-05;;1;;nein;2026-11-01T10:00:00+01:00;Individuelle Vereinbarung ungeklärt
```

- **1001:** 200 € bereits erhalten, keine neue Lastschrift.
- **1002:** 100 € erhalten; nur die letzten beiden vereinbarten Monatsraten à 50 €
  sind offen. Die ursprüngliche Ratenzahl bleibt 4, die offenen Raten werden als
  Nummern 3 und 4 übernommen. Beim Import bleiben ihre Termine am 20. erhalten.
  Der vorhandene SEPA-Export verwendet anschließend seinen tatsächlichen Banktermin.
- **1003:** Gesamtbetrag und Beginn bleiben unbekannt. Das tatsächliche frühere
  Anfragedatum sowie 25 € Eingang werden übernommen; keine Forderung, Befreiung,
  Lastschrift oder Benachrichtigung wird daraus automatisch abgeleitet.

`Einlage Stichtag` dokumentiert den kumulierten historischen Eingangsbestand,
nicht einzelne Bankumsätze. `Einlage Beleg` nennt die geprüfte Quelle/Vereinbarung.
Geldbeträge dürfen Punkt oder Komma, aber keine Tausenderzeichen enthalten.
Offene Raten stehen als `Datum:Betrag`, getrennt durch `|`, chronologisch monatlich
und frühestens ab dem vereinbarten Beginn. Höchstens 12 Raten sind möglich. Ihre
Summe muss genau `max(Gesamt − Erhalten, 0)` ergeben; bereits erhaltene Raten fehlen
in dieser Liste. Ein Plan von 100 €, davon 25 € erhalten und viermal `18,75` offen,
kann mit `Einlage Individuell=ja` übernommen werden. Ein ausdrücklicher Verzicht
hat Gesamtbetrag 0, bekannten Beginn, Ratenzahl 1 und keine offenen Raten.

Der erste erfolgreiche Eröffnungsstand wird auditiert. Eine identische normalisierte
Wiederholung erzeugt keine weiteren Buchungen, Raten oder Logs, auch nach späterem
Export oder neuer Verwaltungsvereinbarung. Abweichende kumulierte Stände werden
abgewiesen, auch mit `--update yes`; Korrekturen über die Einlagenverwaltung klären.
Bereits verwendete Konten ohne diesen Importnachweis werden nicht überschrieben.
Historische Rückzahlungen separat über die vorhandene Rückzahlungsverwaltung
dokumentieren; nicht als neue offene Raten oder unbemerkt verringerte Eingänge erfassen.

Im normalen `members`-Import bleiben ausgelassene/leere Mitgliedschaftsangaben bei
vorhandenem Einlagenkonto erhalten. Widersprüchliche oder mehrphasige Ersetzungen
werden vor Profil-/Keycloak-Änderungen abgewiesen. Solche Änderungen über die Verwaltung
bearbeiten. Einlagenfelder gehören in die separate `deposits`-Datei.
