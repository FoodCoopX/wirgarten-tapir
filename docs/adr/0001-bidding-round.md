# ADR 0001: Beitragsrunde (Bietrunde) in Tapir

- **Status:** angenommen, umgesetzt in `feat/bidding_round_v2` (Issue #1311)
- **Datum:** 2026-10-30
- **Kontext:** Tapir (`FoodCoopX/wirgarten-tapir`), Zielinstanz Solawi Vierlande
- **Quellen:** [Issue #1311](https://github.com/FoodCoopX/wirgarten-tapir/issues/1311),
  [Anforderungsdokument „Beitragsrunde (Bietrunde) in Tapir" (Gist)](https://gist.github.com/yeoldegrove/f9dcf17110ec57ed31d68e4286d84904)

## Problem

Bei Solawi Vierlande legt die Mitgliedschaft jedes Jahr in einer Beitragsrunde selbst fest, wie viel
ihr Ernteanteil kosten soll. Bisher läuft das außerhalb von Tapir. Tapir kennt die Ernteanteile, die
Vertragsperioden, die automatische Verlängerung und die Solidaritätsbeiträge, aber keinen Weg, ein
Gebot abzugeben, die Gebote auszuwerten und daraus die Verträge der kommenden Saison zu erzeugen.

Zwei Dinge machen das nicht trivial:

1. **Nicht jedes Mitglied beteiligt sich.** Wer nicht bietet, zahlt trotzdem: laut Beitragsordnung
   den Richtwert bzw. das durchschnittliche Gebot der Bietenden. Automatisch verlängerte Verträge
   müssen also nachträglich auf die neuen Konditionen angepasst werden.
2. **Die Saison muss am Ende finanziert sein.** Deshalb braucht es eine Auswertung, die live zeigt,
   wie viel Deckung die abgegebenen Gebote ergeben, und eine Empfehlung, welches Gebotsniveau man
   zur Vertragserzeugung heranzieht.

Dazu kommt die Frage, wie sich Neu-Mitglieder verhalten, die während einer Runde über den
Bestell-Wizard dazukommen: Wenn eine Runde scheitert, während schon Verträge für Neu-Mitglieder
laufen, entsteht ein Zustand, den niemand sauber auflösen kann.

## Entscheidungen

### E1 — Während der Runde bieten nur eingeloggte Bestandsmitglieder

Die Seite `/bidding_rounds/` ist login-gated. Wer nicht eingeloggt ist, sieht Intro und
Anmelde-Button (Keycloak), aber keine Registrierung und keinen „Mitglied werden"-Weg. Neue
Mitglieder entstehen weiterhin ausschließlich über den Bestell-Wizard, also **vor oder nach** der
Runde. Es gibt keinen `register`-Endpunkt, keinen Wartelisten-Zweig und keine Kapazitätsprüfung ohne
Mitglied.

*Begründung:* Es hält den Teilnehmerkreis stabil und vermeidet den Konflikt „Runde scheitert,
Neu-Mitglied hat schon einen Vertrag". In der Diskussion war das der Punkt, an dem alle Beteiligten
die höchste Komplexität gesehen haben.

*Konsequenz:* Eine volle Saison hängt an der Vorab-Akquise über den Bestell-Wizard. Für den Anfang
ist das gewollt; eine Teilnahme von Neu-Mitgliedern wäre eine eigene Entscheidung.

### E2 — Eine Seite plus Hinweis im Mitgliederbereich

`/bidding_rounds/` bleibt die einzige Gebotsseite, zusätzlich erscheint bei aktiver Runde ein Hinweis
im Mitgliederbereich (`member_detail.html`), damit Mitglieder die Runde nicht verpassen.

*Begründung:* Marcus hat vorgeschlagen, die Gebotsabgabe ganz in den Mitgliederbereich zu holen, weil
Bestandsmitglieder den Weg über die Seite nicht brauchen. Der Hinweis deckt das Bedürfnis ab, ohne
das Intro (das den Login trägt) in den Mitgliederbereich zu verschieben.

### E3 — Ein Abholort, kein Zweitwunsch

Der eigene Abholort wird immer angezeigt. Geändert werden kann er nur, wenn
`BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED` aktiv ist; dann läuft beim Wechsel ein
Kapazitäts-Check. Ist der Zielort voll, ist kein Wechsel möglich. Es gibt keinen Zweitwunsch und
keinen Fallback.

*Begründung:* Ein zweiter Wunsch beschreibt eine Zuordnung, die später jemand auflösen muss.
Kapazitätskonflikte löst der Admin manuell in der Auswertung; das ist ehrlicher als ein
Automatismus, der Gebote nachträglich umverteilt.

### E4 — Nur der Modus `SOLIDARITY`

Es gibt keine Auswahl eines Beitragsmodus. Ein Gebot wird immer als Standardpreis plus Differenz in
`SolidarityContribution` abgebildet (negative Differenz = Ermäßigung). `PRICE_OVERRIDE`
(`Subscription.price_override`) wird nicht verwendet.

*Begründung:* Solange die Beitragsrunde der einzige Weg ist, über den Gebote in Verträge fließen,
ist der zweite Modus eine Fallunterscheidung ohne Nutzen.

### E5 — Rundenwerte hängen an der Runde, nicht an `ProductCapacity`

Neue Modelle `BiddingRoundProduct` (Zielbetrag pro Jahr) und `BiddingRoundProductPrice`
(`reference_value`, `min_amount` je Anteilsgröße) gehören zur Runde und werden in der
Rundenkonfiguration gepflegt — nicht im Produkt-Konfigurator und nicht an `ProductCapacity`.

*Begründung:* `ProductCapacity` gilt pro Vertragsperiode; in einer Periode können aber zwei Runden
stattfinden (z. B. wenn die erste scheitert). Die zweite Runde muss eigene Werte haben, ohne die
Auswertung der ersten zu verändern. Außerdem skalieren die Preise nicht linear mit einer
Größenangabe (Théo), sie sind je Anteilsgröße manuell zu setzen. Nach der Runde werden die
ermittelten Beträge wie gewohnt in die Produkttypen der Vertragsperiode geschrieben.

*Konsequenz:* Der Produkt-Konfigurator bleibt unberührt. Eine Runde kann genau eine bietbare
Produktart haben; mehrere wären eine Modelländerung.

### E6 — Durchschnittsgebot wird gesperrt

`lock_average_bid` bleibt: Vor der Vertragserzeugung wird das durchschnittliche Gebot (bzw. die
Ampelposition und der Lieferzuschlag) fixiert.

*Begründung:* Statistik, Vertragserzeugung und Bestätigungsmail müssen denselben Betrag verwenden.
Ohne Sperre würde der Durchschnitt sich während der Vertragserzeugung weiterbewegen.

### E7 — `SIMPLE` mit 1–3 Stufen

Das einfache Verfahren erlaubt ein bis drei Beträge (`bid_levels`, 1–3). Reicht der Wunschbetrag
nicht, gilt der nächste. Beim Ampelverfahren gibt es Grün (Wunsch), Gelb (Zufrieden) und Rot
(Schmerzgrenze).

*Begründung:* Vierlande lässt seit Jahren bis zu drei Gebote zu, um sich mehrere Runden zu sparen.
Der Vorstand wählt nach der Auswertung eine Stufe. Das Ampelverfahren kam als zweites Verfahren
dazu, weil es dieselbe Information in einer Form abfragt, die Mitglieder leichter beantworten können.
Das eigene Gebot bekommt bewusst keine Ampel-Bewertung angezeigt — weder während noch nach dem
Absenden.

### E8 — Manuelle Gebote bleiben möglich

Der Admin kann Gebote anlegen, ändern und löschen (`entered_by_admin`, `admin_confirmed`). Nach der
Vertragserzeugung ist das blockiert, auch ein reiner Abholortwechsel.

*Begründung:* In der Praxis gibt es Korrekturfälle (Telefon, Papier, Tippfehler). Ein
Nachtragen nach der Vertragserzeugung würde dagegen den erzeugten Verträgen widersprechen.

### E9 — Harte Feature-Flags

| `BIDDING_ROUND_ENABLED` | `BIDDING_ROUND_URL_ENABLED` | Mitgliederseite + öffentliche APIs | Admin-Seiten/APIs |
|---|---|---|---|
| `false` | egal | 404 | 404 |
| `true` | `true` | 200 | 200 |
| `true` | `false` | 404 | 200 |

Das `BIDDING_ROUND_ENABLED`-Gate sitzt als Mixin/Permission vor allen Views, nicht in den Templates.
Die dritte Flag, `BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED`, steuert ausschließlich das
*Ändern* des Abholorts; Anzeigen ist immer aktiv und ein trotzdem mitgeschickter
`pickup_location_id` wird serverseitig ignoriert.

*Begründung:* Die Runde ist eine Funktion, die nur für einen Teil der Organisationen relevant ist, und sie
muss sich komplett abschalten lassen. Ein 404 auf allen Ebenen ist
leichter zu prüfen als ein halb ausgeblendeter Zustand.

### E10 — Vertragserzeugung arbeitet mit Vorschlägen, nicht mit Automatik

Erzeugt werden nur bestätigte Gebote, und nur nachdem die Runde geschlossen ist. Bestehende, nicht
gekündigte Verträge desselben Mitglieds und Produkts in der Zielperiode werden ersetzt; vorher wird
ihr Zustand als `BiddingRoundReplacedSubscription` gesichert (inklusive Lieferungen,
Verknüpfungen und Preis-Log-Zuordnung), damit ein Löschen der Rundenverträge sie zurückbringt.
Kapazitätskonflikte brechen nicht die ganze Erzeugung ab, sondern landen als Fehlerbericht je Gebot.

*Begründung:* Die Vertragserzeugung schreibt in Daten, die Mitglieder vertraglich binden. Sie muss
nachvollziehbar bleiben: was wurde ersetzt, was wurde erzeugt, was ist schiefgegangen.

## Datenmodell

```
BiddingRound            growing_period, name, status, bidding_procedure, bid_levels (1–3),
                        start_at, end_at, include_auto_renewed, contracts_created_at,
                        average_bid_locked_at, locked_*   (CheckConstraint: bid_levels 1–3)
BiddingRoundProduct     round, product_type, target_amount_per_year
BiddingRoundProductPrice round_product, product, reference_value, min_amount
Bid                     round, member, pickup_location, entered_by_admin, admin_confirmed
                        (UniqueConstraint: round + member)
BidItem                 bid, round_product, product, quantity (1–5), amount_1..amount_3
                        (CheckConstraint: quantity 1–5)
BiddingRoundCreatedSubscription   round, subscription, is_bidder_contract
BiddingRoundReplacedSubscription  round, data (JSON-Snapshot der ersetzten Verträge)
```

Ein `RunPython`-Backfill in der initialen Migration `0001` klemmt bestehende Werte (`bid_levels` auf 1–3,
`quantity` auf 1–5), bevor die CheckConstraints gesetzt werden.

## Konsequenzen

**Gut:** Der Teilnehmerkreis ist stabil, die Auswertung ist live und nachvollziehbar, die
Vertragserzeugung lässt sich vor dem Schreiben prüfen und rückgängig machen, und die Funktion lässt
sich mit einer Flag komplett abschalten.

**Schwierig:** Die Logik für Nicht-Bietende ist verteilt (Runde, Nachzügler, automatische
Verlängerung) und muss konsistent bleiben. Das Ersetzen bestehender Verträge ist der empfindlichste
Teil: Rückabwicklung geht nur über den Snapshot. Die Saisonfinanzierung hängt daran, dass genug
Mitglieder vorab oder später über den Bestell-Wizard kommen.

## Verworfene Alternativen

- **Teilnahme und Registrierung von Neu-Mitgliedern während der Runde** (inkl. Warteliste und
  Kapazitätsprüfung ohne Mitglied): Konflikt zwischen scheiternder Runde und laufenden Verträgen.
- **Zweiter Abholort-Wunsch mit Fallback:** verlagert die Konfliktlösung in einen Automatismus, der
  Gebote umverteilt.
- **`PRICE_OVERRIDE`** als zweiter Modus: keine Anwendung, solange nur die Beitragsrunde Gebote in
  Verträge schreibt.
- **Werte an `ProductCapacity` bzw. Skalierung über `product_price.size`:** nicht linear, und zwei
  Runden pro Periode brauchen getrennte Werte.
- **Eigener öffentlicher Endpunkt für die Gebotsabgabe ohne Login:** widerspricht E1.
- **Frontend-Lokalisierung mit `djangojs`/`/jsi18n/`:** der Aufwand steht in keinem Verhältnis,
  solange Mails und der Rest der Oberfläche nicht übersetzt sind.

## Nicht Teil dieser Entscheidung

Teilnahme von Neu-Mitgliedern während der Runde; mehrere bietbare
Produktarten je Runde; automatische Erinnerungs-Mails; automatische Löschung (DSGVO); Logo und
Erklärungstexte je Runde; regionale Sprachvarianten.

## Risiken

- Der effektive Betrag eines Gebots hängt von Position und Stufe ab; gesperrter Durchschnitt,
  Statistik, Vertragserzeugung und Mail müssen denselben Wert verwenden.
- Genau eine bietbare Produktart je Runde (Modellgrenze).
- Der Non-Bidder-Floor senkt bestehende höhere Beiträge nie — gewollt, aber erklärungsbedürftig.
- Ersetzte Verträge sind nur über den Snapshot wiederherstellbar.

## Referenzen

- Issue [#1311](https://github.com/FoodCoopX/wirgarten-tapir/issues/1311)
- Anforderungsdokument v3 (Gist, siehe oben) — inklusive der Feedback-Tabelle von Marcus, Théo und Eike
- `docs/dev/bidding_round.md` — Flüsse, Feature-Flags und Capacity-Check im Detail
