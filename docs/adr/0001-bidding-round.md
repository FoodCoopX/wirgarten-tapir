# ADR 0001: Beitragsrunde (Bietrunde) in Tapir

- **Status:** angenommen, umgesetzt
- **Datum:** 2026-11-06
- **Kontext:** Tapir (`FoodCoopX/wirgarten-tapir`), Zielinstanz Solawi Vierlande
- **Quellen:** [Issue #1311](https://github.com/FoodCoopX/wirgarten-tapir/issues/1311),
  [Anforderungsdokument „Beitragsrunde (Bietrunde) in Tapir"](https://gist.github.com/yeoldegrove/f9dcf17110ec57ed31d68e4286d84904)

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

## Entscheidungen

### E1 — Während der Runde bieten nur eingeloggte Bestandsmitglieder

Die Seite `/bidding_rounds/` ist login-gated. Wer nicht eingeloggt ist, sieht Intro und
Anmelde-Button (Keycloak), aber keine Registrierung und keinen „Mitglied werden"-Weg. Neue
Mitglieder entstehen weiterhin ausschließlich über den Bestell-Wizard, also **vor oder nach** der
Runde.

*Begründung:* Das hält den Teilnehmerkreis stabil und vermeidet den Konflikt „Runde scheitert,
Neu-Mitglied hat schon einen Vertrag". In der Diskussion war das der Punkt, an dem alle Beteiligten
die höchste Komplexität gesehen haben.

### E2 — Eine Seite plus Hinweis im Mitgliederbereich

`/bidding_rounds/` bleibt die einzige Gebotsseite; zusätzlich erscheint bei aktiver Runde ein
Button im Mitgliederbereich, damit Mitglieder die Runde nicht verpassen.

*Begründung:* Marcus hat vorgeschlagen, die Gebotsabgabe ganz in den Mitgliederbereich zu holen. Der
Hinweis deckt das Bedürfnis ab, ohne das Intro (das den Login trägt) in den Mitgliederbereich zu
verschieben.

### E3 — Abholort wird nur angezeigt, nicht geändert

Der eigene Abholort und sein jährlicher Lieferzuschlag werden im Gebotsablauf und in der
Zusammenfassung angezeigt. Ein Wechsel entfällt; die Kapazitätsprüfung erfolgt beim Erzeugen der
Verträge, ein Tooltip verweist auf den Mitgliederbereich.

Umgesetzt ohne Kopie am Gebot: `Bid` speichert keinen Abholort; Auswertung, CSV, Mails und
Vertragserzeugung lesen den Ort des Mitglieds zum Vertragsbeginn über `MemberPickupLocationGetter`.

*Begründung:* Der Abholort ist bereits am Mitglied gepflegt und die Verträge übernehmen ihn. Ein
Wechsel hätte einen eigenen Kapazitäts-Check beim Gebot, zusätzliche Pickup-Refactors und eine
Testdaten-Runde gebraucht — Aufwand und Fehlerfläche stehen in keinem Verhältnis zum Nutzen in der
ersten Version.

### E4 — Preis-Modus und eingefrorener Rundenpreis statt manuellem Override

`Subscription.price_mode` unterscheidet `standard`, `custom`, `free`, `bidding_round_bid` und
`bidding_round_auto_renewed`. `price_override` bleibt der allgemeine Admin-Override und hat Vorrang
vor jedem Modus, auch als `0`; die Bietrunden-Modi sind in der Preis-Maske deaktiviert und werden
nur von der Bietrunde gesetzt.

Der Preis eines Bietrunden-Vertrags hängt vom Rundenergebnis ab, nicht von `ProductPrice`:
`ProductPrice` kennt keine Herkunft „Preis aus Runde X", ein späterer Katalogpreis würde sonst
bereits fixierte Verträge still verschieben. Deshalb friert
`BiddingRoundCreatedSubscription.monthly_price_per_share` den Anteilspreis beim Anlegen des
Vertrags ein:

- Bieter-Verträge: das fixierte Durchschnittsgebot der Bietenden je Anteil, skaliert mit der
  Anteilsgröße der Runde.
- Automatisch verlängerte Verträge: `max(reference_value, Bietenden-Durchschnitt)` je Anteil,
  skaliert mit der Anteilsgröße der Runde.

Der Monatspreis ist dieser eingefrorene Anteilspreis mal Menge. Er ändert sich auch dann nicht,
wenn die Runde oder `ProductPrice` später angepasst werden. `ProductPrice` bleibt eine Projektion;
„Standardpreis angleichen" schreibt den fixierten Durchschnitt × Rundengröße in den Katalog, damit
alle Pfade, die `ProductPrice` lesen, wieder übereinstimmen. Queryset-Annotationen für
Mitglieder- und Vertragslisten lesen denselben eingefrorenen Wert (siehe
`BiddingRoundSubscriptionPriceService`), damit Listen den Rundenpreis auch vor dem Angleichen
zeigen.

Die Finanzierungsprojektion der Auswertungsseite ist ein Was-wäre-wenn mit zielgedecktem
Durchschnitt und ändert keine Vertragspreise.

### E5 — Bietrunden-Werte je Runde und Anteilsgröße

`BiddingRoundProductPrice` hält `reference_value` und `min_amount` je Produkt (Anteilsgröße), der
Zielbetrag pro Jahr liegt direkt an `BiddingRound`. `reference_value` und `min_amount` gelten 1:1 je
Anteil; der Vertragspreis multipliziert den Anteilspreis mit `BiddingRoundProductPrice.size`.
`ProductCapacity` bleibt unverändert.

*Begründung:* Théo und Marcus wollten die Werte pro Anteilsgröße manuell pflegen und nicht linear
skalieren. Werte an der Runde statt am Produkt halten zwei Runden pro Periode auseinander und lassen
die Auswertung der ersten Runde stabil.

### E6 — Durchschnittsgebot sperren

Vor der Vertragserzeugung wird das Durchschnittsgebot samt Position und Aufschlag fixiert. Das
Sperren ist nur für eine `CLOSED`-Runde erlaubt. Die fixierte Position ist der Default für
Auswertung, Mails und Verträge; ein explizit angeforderter `bid_range_position` steuert weiterhin
die angezeigten effektiven Beträge. Nach dem Fixieren sind sowohl Admin- als auch Mitgliedsgebote
gesperrt; Freigeben ist nach der Vertragserzeugung nicht mehr erlaubt, solange die erzeugten
Verträge existieren.

Gespeichert wird nur der Monatswert je Anteil; der Jahreswert wird beim Lesen als `× 12` abgeleitet.

### E7 — SIMPLE mit 1–3 Stufen, BID_RANGE (Gebotsspanne) mit zwei festen Beträgen

`SIMPLE` erlaubt eine bis drei aufsteigende Beträge. `BID_RANGE` (historisch `TRAFFIC_LIGHT`, DB-Wert
`bid_range`) nutzt immer zwei Stufen: Grün (Wunsch) und Rot (Schmerzgrenze); beide sind Pflicht, ein
dritter Betrag ist nicht erlaubt. Die Auswertung interpoliert linear auf einer 0/100-Achse; Position
50 ist der Mittelpunkt und Backend-Default. Die alten Gelb-Beträge entfallen; Migration `0002`
führt Verfahren und Stufen ein. Da das Feature unveröffentlicht ist, gibt es keine Datenmigration
für bestehende Runden. Die Felder/API heißen `locked_bid_range_position` und
`bid_range_position`.


### E8 — Backend-gettext, Frontend ohne Lokalisierung

Das Backend nutzt `gettext_lazy` mit deutschen msgids und ohne separaten Katalog. Das Frontend nutzt
deutsche String-Literale ohne `/jsi18n/`.

*Begründung:* Tapir hat noch keine Frontend-Lokalisierung; eine halbe Einführung hätte mehr
verwirrt als geholfen. Bewusste Abweichung von der allgemeinen Projektregel für diese erste Version.

### E9 — Manuelle Admin-Gebote bleiben

Admins können Gebote anlegen, ändern und löschen (Konflikt- oder Korrekturfälle). Nach dem
Fixieren des Durchschnittsgebots sind Gebotsänderungen blockiert.

### E10 — Harte Feature-Flag-Gates

`BIDDING_ROUND_ENABLED=false` liefert auf allen Seiten und Endpunkten 404.
`BIDDING_ROUND_URL_ENABLED=false` leitet anonyme Besucher der öffentlichen Seite zum Keycloak-Login
um; angemeldete Mitglieder behalten Seite und API, die Admin-Seiten bleiben erreichbar. Damit sind
die Schichten einzeln deploybar und nichts Halbes ist öffentlich sichtbar.

`BIDDING_ROUND_STATUS_ENABLED` blendet den Zwischenstand für alle aus, `BIDDING_ROUND_STATUS_PUBLIC_ENABLED`
erlaubt ihn zusätzlich anonym. Beide Gates schützen nur den Status-Endpunkt, nicht das Bieten.

### E11 — Nicht-Bietende einbeziehen, mit Floor

Automatisch verlängerte Mitglieder fließen mit ihrem Richtwert in die Auswertung ein
(`include_auto_renewed`). Nicht-Bietende zahlen mindestens den Bietenden-Durchschnitt
pro Anteil; bestehende höhere Beiträge werden nie gesenkt. Nachzügler über den Bestell-Wizard
bekommen denselben Floor. Der Floor ist immer aktiv; es gibt keinen Parameter mehr.

### E12 — Anteile pro Gebot

Ein Gebot kann 1–5 Anteile enthalten. Die Beträge gelten pro Anteil; Monats- und Jahressummen
multiplizieren mit der Anzahl.

### E13 — Auswertungs-UI wie der alte Stand, mitgliedsscharfer Rollback und `is_bidder_contract`

Die Auswertungsseite portiert den alten Stand: Finanzierung mit Gebotsspanne/Slider, Beispielen,
„Wie wird gerechnet?“ und 12-Monats-Prognose, Abholort-Füllstand, eine Gebote-Tabelle mit allen
Mitgliedern und die Verträge-Karte mit Prüfen/Erzeugen/Zurücknehmen. `Alle bestätigen` und `CSV`
bleiben zusätzlich sichtbar; Gebote erfasst man über `Gebot erfassen` in der Toolbar oder
pro Tabellenzeile (dort mit vorausgewähltem Mitglied). Die Gebote-Tabelle zeigt keine
E-Mail-Spalte.

`BiddingRoundCreatedSubscription.is_bidder_contract` trennt Bieter- von Auto-Verlängerer-Verträgen.
Jeder Schreibvorgang einer Runde läuft zusätzlich in einem `BiddingRoundMemberEffect`: Er hält den
serialisierten Vorzustand der Subscriptions und Solidaritätsbeiträge des Mitglieds, den
Nachzustand, die Beitrags-Log-Verknüpfungen und die Mandatsreferenzen fest. `rollback_members`
spielt diesen Vorzustand pro Mitglied oder für die ganze Runde zurück, einschließlich der
Beitragshistorie; es gibt keinen Recompute mehr aus dem aktuellen Datenbestand.
Abweichungen seit der Erzeugung blockieren den Rollback, sofern er nicht mit `force` und Begründung
erzwungen wird. Hängt eine andere Runde an denselben Verträgen, wird der Rollback immer verweigert;
die neuere Runde wird zuerst zurückgenommen. Runden aus der Zeit vor dem Effekt-Ledger sind nicht
automatisch rückrollbar. Der alte Precheck pro Gebot wird nicht portiert; die Vertragserzeugung
prüft die Runde gegen die Anteils- und Abholort-Kapazität, `check_contracts` meldet zusätzlich
unbestätigte Gebote.

*Begründung:* Die alte Auswertung ist die Arbeitsgrundlage der Beitragsrunde; der neue Stack hatte
nur einen vereinfachten Port. Der aufgezeichnete Vorzustand macht einen fehlerhaften Lauf
wiederholbar, ohne fremde Beitragsstände zu zerstören oder spätere manuelle Änderungen zu
überschreiben.

### E14 — Checkout-Flow mit optionalen Schritten und finaler Summary

Nach dem Gebot folgt ein Checkout-Flow aus optionaler SEPA-Seite, Datenschutz-Seite, optionaler
Feedback-Seite und der finalen „Dein Gebot“-Summary. SEPA und Feedback sind per Parameter
(`BIDDING_ROUND_SEPA_ENABLED`, `BIDDING_ROUND_FEEDBACK_ENABLED`, beide Default `true`) zu- und
abschaltbar; Datenschutz und Summary sind immer Teil des Flows. Die SEPA-Seite übernimmt
Kontoinhaber, IBAN und Zahlungsrhythmus aus dem Mitglied; die SEPA-Zustimmung
(`member.sepa_consent`) wird beim Gebot gespeichert, die Mandatsreferenz entsteht bei der
Vertragserzeugung. Die Datenschutz-Seite ist ein eigener Schritt mit Pflicht-Checkbox.

Die Feedback-Seite verwendet `Step13Feedback` aus dem Bestell-Wizard mit `isOrderStep={false}`
wieder; Titel und Text kommen aus dessen Schritt-13-Strings. Nicht-leeres Feedback wird beim
Absenden als `OrderFeedback` mit Rundenbezug am Mitglied gespeichert und bei erneutem Absenden
aktualisiert.

Die finale Summary zeigt Accordions für Produkt (Anteile, Gebotsstufen, Jahresbetrag, Abholort,
„Gebot anpassen“), Vereinsmitgliedschaft (nur bei aktiver Mitgliedschaft und ohne Waiver, mit
Monatspreis) und „Deine Zahlungen“ mit der Kostenaufstellung je Gebot: Monatsbetrag, Jahresbetrag,
Vereinsmitgliedschaft und Lieferkosten, jeweils nur wenn sie anfallen, darunter die Gesamtsummen.
Einen Datenschutzblock und einen Warenkorb gibt es dort nicht. Der Summary-Titel kommt aus
`BIDDING_ROUND_PUBLIC_SUMMARY_TITLE` und ersetzt `{vorname}` durch den Vornamen des Mitglieds; der
finale Button-Text kommt aus `BIDDING_ROUND_PUBLIC_FINAL_SUBMIT_LABEL`. Die Defaults stehen in
den Parameterdefinitionen; da das Feature unveröffentlicht ist, gibt es keine Datenmigration.

*Begründung:* Der Checkout nutzt die vorhandene Wizard-Hülle und die Bestell-Wizard-Bausteine,
statt eine zweite Optik zu bauen. Ein separater Datenschutz-Schritt hält die Zustimmung aus der
Zusammenfassung heraus; SEPA und Feedback bleiben pro Instanz abschaltbar, weil nicht jede Solawi
Bankdaten in der Runde erhebt oder Feedback einsammeln möchte. Die Vereinsmitgliedschaft wird nur
angezeigt, wenn sie tatsächlich aktiv ist, damit die Summary keine Zahlung suggeriert, die nicht
anfällt.

### E15 — Vereinsbeiträge entfallen bei Produkten

Der Parameter `ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS` erlässt Mitgliedern mit
mindestens einem Produktvertrag den Vereinsbeitrag. Die Regel liegt in der Zahlungserzeugung; die
Bietrunden-Auswertung und die finale Summary lassen die Mitgliedschaftsposition weg, weil jedes
Gebot zu einem Produktvertrag führt. Der Bestell-Wizard zeigt den Preis weiterhin an, weil der
Waiver eine Zahlungsregel und keine Preisänderung ist.

*Begründung:* In VIERLANDE finanzieren die Produktbeiträge den Verein; ein zusätzlicher
Mitgliedsbeitrag für Produkthalter wäre eine Doppelbelastung. Die Bietrunden-Summary zeigt die
tatsächlichen Zahlungen und darf deshalb keine Mitgliedschaftskosten suggerieren.

## Konsequenzen

- Die Runde ist vollständig in Tapir abbildbar, ohne externe Tabellen oder manuelle Vertragserzeugung.
- Der Abholort bleibt außerhalb der Runde pflegbar; die Bietrunde kann keine Kapazität überbuchen,
  weil sie keine Orte vergibt.
- Die Auswertung ist live und reproduzierbar: Sperren friert die Werte ein, die Verträge nutzen
  exakt diese Werte.
- Automatisch verlängerte und nicht bietende Mitglieder bleiben konsistent, ohne dass jemand manuell
  Beiträge nachpflegen muss.
- Ein fehlerhafter Vertragslauf lässt sich über `rollback_members` pro Mitglied oder für die ganze
  Runde zurücknehmen; der aufgezeichnete Vorzustand der Verträge und Beitragsanpassungen wird
  wiederhergestellt.
- Offen für spätere Schichten: ein Abholort-Wechsel mit Kapazitätsprüfung, weitere Verfahren.
