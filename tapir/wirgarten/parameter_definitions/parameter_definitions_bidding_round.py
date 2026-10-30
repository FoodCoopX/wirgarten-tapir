import typing

from django.utils.translation import gettext_noop

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsBiddingRound:
    @classmethod
    def define_all_parameters_bidding_round(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_ENABLED,
            label=gettext_noop("Beitragsrunde aktivieren"),
            description=gettext_noop(
                "Hauptschalter für die Beitragsrunde. Wenn deaktiviert, sind alle Beitragsrunden-Seiten nicht erreichbar."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=10,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_URL_ENABLED,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite aktivieren"),
            description=gettext_noop(
                "Aktiviert nur den öffentlichen Endpunkt der Beitragsrunde. Die Admin-Seiten bleiben erreichbar."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=9,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED,
            label=gettext_noop("Abholort-Wechsel in der Beitragsrunde erlauben"),
            description=gettext_noop(
                "Wenn aktiviert, können Mitglieder beim Bieten ihren Abholort ändern, solange am gewählten Ort freie Kapazität ist. Der eigene Abholort wird immer angezeigt."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=8,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_STATS_INCLUDE_AUTO_RENEWED,
            label=gettext_noop(
                "Automatisch verlängerte Mitglieder in die Auswertung einbeziehen"
            ),
            description=gettext_noop(
                "Wenn aktiviert, werden Mitglieder ohne Gebot, deren Vertrag automatisch verlängert wird, mit ihrem Richtwert in die Auswertung einbezogen."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_STATS_MEMBERSHIP_INCLUDED_IN_PRODUCT_TYPE,
            label=gettext_noop("Mitgliedschaft im Ernteanteil berücksichtigen"),
            description=gettext_noop(
                "Wenn aktiviert, wird die Mitgliedschaft von Mitgliedern mit bezahlter Mitgliedschaft nicht separat berechnet, sondern im Ernteanteil mitgeführt (statt als eigener Posten in der Zeile der Ernteanteile ausgewiesen)."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_NON_BIDDERS_MIN_AVERAGE,
            label=gettext_noop(
                "Nicht-Bietende zahlen mindestens das durchschnittliche Gebot"
            ),
            description=gettext_noop(
                "Wenn aktiviert, zahlen Nicht-Bietende (automatisch Verlängerte und Nachzügler) mindestens das durchschnittliche Gebot der Bietenden. Überdurchschnittliche Gebote führen dann zu einem Überschuss (Solidaritätsfonds)."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED,
            label=gettext_noop("Beitragsrunde: Anzahl Anteile anzeigen"),
            description=gettext_noop(
                "Wenn aktiviert, können Mitglieder die Anzahl der Anteile pro Posten angeben. Standardmäßig ist genau ein Anteil gesetzt."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Titel"),
            description=gettext_noop("Titel der öffentlichen Beitragsrunden-Seite."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Beitragsrunde",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Einführungstext"),
            description=gettext_noop(
                "Einführungstext auf der öffentlichen Beitragsrunden-Seite."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="In der Beitragsrunde bestimmst du selbst, wie viel dein Ernteanteil kostet. Mit deinem Beitrag finanzierst du die Saison und sorgst dafür, dass die Solidarität in unserer Gemeinschaft wächst.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
            label=gettext_noop(
                "Öffentliche Beitragsrunden-Seite: Text, wenn keine Beitragsrunde aktiv ist"
            ),
            description=gettext_noop(
                "Wird angezeigt, wenn keine Beitragsrunde aktiv ist oder bereits beendet wurde. Eine Anmeldung über die Beitragsrunden-Seite ist nicht möglich."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value='Die aktuelle Beitragsrunde ist beendet. Du kannst jederzeit Mitglied werden – über unseren <a href="/bestell_wizard/bestell_wizard_mobile">Bestell-Wizard</a> gelangst du direkt zur Anmeldung. Wir freuen uns auf dich!',
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Titel Anmeldung"),
            description=gettext_noop(
                "Titel des Anmeldeblocks für bestehende Mitglieder."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du bist bereits Mitglied?",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TEXT,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Text Anmeldung"),
            description=gettext_noop(
                "Text des Anmeldeblocks für bestehende Mitglieder."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Melde dich an, um dein Gebot abzugeben oder zu ändern.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TITLE,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Titel Abholort"),
            description=gettext_noop("Titel des Schritts Abholort."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Abholort",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TEXT,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Text Abholort"),
            description=gettext_noop(
                "Text of the pickup location step. Your own pickup location is always "
                "shown; it can only be changed if the corresponding setting is enabled."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Das ist dein aktueller Abholort. Wenn an einer anderen Station Kapazität frei ist, kannst du ihn hier ändern.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_SUMMARY_TITLE,
            label=gettext_noop(
                "Öffentliche Beitragsrunden-Seite: Titel Gebotsübersicht"
            ),
            description=gettext_noop(
                "Titel des Schritts, in dem das Gebot zusammengefasst und abgeschickt wird."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein Gebot",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_SUBMIT_LABEL,
            label=gettext_noop(
                "Öffentliche Beitragsrunden-Seite: Beschriftung Gebot abgeben"
            ),
            description=gettext_noop(
                "Beschriftung der Schaltfläche zum Absenden des Gebots."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot abgeben",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TITLE,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Titel Zwischenstand"),
            description=gettext_noop(
                "Titel des öffentlichen Zwischenstands der Beitragsrunde."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Zwischenstand",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TEXT,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Text Zwischenstand"),
            description=gettext_noop(
                "Text of the public progress of the bidding round."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="So viel ist von der zu finanzierenden Summe der Saison bereits erreicht:",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_EXPLANATION,
            label=gettext_noop(
                "Öffentliche Beitragsrunden-Seite: Erklärung Zwischenstand"
            ),
            description=gettext_noop(
                "Erklärt im öffentlichen Zwischenstand, was Auslastung, Deckung und das durchschnittliche Gebot der Bietenden bedeuten."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Zwischenstand zeigt, wie die Beitragsrunde gerade steht. „Aktuelle Auslastung“ sagt, wie viele Ernteanteile schon gewünscht sind. „Aktuelle Deckung“ zeigt, wie viel Geld von der Summe, die die Saison kostet, schon zusammenkommt. „Bietende Ø“ ist der durchschnittliche Betrag pro Anteil und Monat, den die Bietenden angeben.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TRAFFIC_LIGHT_SLIDER_HINT,
            label=gettext_noop("Öffentliche Beitragsrunden-Seite: Hinweis Ampelregler"),
            description=gettext_noop(
                "Erklärung des Solidaritätsreglers in der öffentlichen Auswertung."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Regler zeigt das Solidaritätsniveau von Grün (Wunsch) über Gelb (Zufrieden) bis Rot (Schmerzgrenze). Deckung und Auslastung unten passen sich an.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_SIMPLE_LEVELS_SLIDER_HINT,
            label=gettext_noop(
                "Öffentliche Beitragsrunden-Seite: Hinweis Stufenregler"
            ),
            description=gettext_noop(
                "Erklärung des Stufenreglers in der öffentlichen Auswertung."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Regler wechselt zwischen den Gebotsstufen. Deckung und Auslastung unten passen sich an.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_QUANTITY_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Anteile"),
            description=gettext_noop(
                "Beschriftung der Anteils-Auswahl im Gebotsformular."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Anzahl Anteile",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_AMOUNT_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Betrag"),
            description=gettext_noop(
                "Beschriftung des Betragsfelds im Gebotsformular."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein Gebot (€/Monat)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_REFERENCE_VALUE_HINT,
            label=gettext_noop("Beitragsrunde: Hinweis Richtwert"),
            description=gettext_noop("Verfügbare Variable: {reference_value}"),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Richtwert liegt bei {reference_value} €/Monat.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(vars_hint=["reference_value"]),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_SIMPLE_EXPLANATION,
            label=gettext_noop("Beitragsrunde: Erklärung einfaches Gebot"),
            description=gettext_noop(
                "Erklärungstext für das einfache Gebot (ein Betrag)."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du gibst einen Betrag an: So viel möchtest du pro Monat für deinen Ernteanteil zahlen. Der Betrag gilt für die ganze Saison.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_TRAFFIC_LIGHT_EXPLANATION,
            label=gettext_noop("Beitragsrunde: Erklärung Ampel-Gebot"),
            description=gettext_noop(
                "Erklärungstext für das Ampel-Gebot (drei Beträge)."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du gibst drei Beträge an: Grün ist dein Wunsch, Gelb ist der Betrag, mit dem du zufrieden bist, und Rot ist deine Schmerzgrenze. Der Gelb-Betrag zählt für deinen Vertrag. Grün und Rot zeigen, wie viel Spielraum du hast.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_SIMPLE_LEVELS_EXPLANATION,
            label=gettext_noop(
                "Beitragsrunde: Erklärung einfaches Gebot (mehrere Stufen)"
            ),
            description=gettext_noop(
                "Explanation text for a simple bid with several levels."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du gibst mehrere Beträge an (Gebot 1 bis Gebot 3). Gebot 1 ist dein Wunschbetrag. Reicht dieser nicht, gilt automatisch Gebot 2, danach Gebot 3. Das letzte Gebot ist deine Schmerzgrenze.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LEVEL_1_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Gebotsstufe 1"),
            description=gettext_noop(
                "Beschriftung der ersten Gebotsstufe im einfachen Gebot."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot 1",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LEVEL_2_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Gebotsstufe 2"),
            description=gettext_noop(
                "Beschriftung der zweiten Gebotsstufe im einfachen Gebot."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot 2",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LEVEL_3_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Gebotsstufe 3"),
            description=gettext_noop(
                "Beschriftung der dritten Gebotsstufe im einfachen Gebot."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot 3",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_GREEN_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Grün"),
            description=gettext_noop(
                "Beschriftung des grünen Betrags (Wunsch) im Ampel-Gebot."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Grün (Wunsch)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_YELLOW_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Gelb"),
            description=gettext_noop(
                "Beschriftung des gelben Betrags (Zufrieden) im Ampel-Gebot."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gelb (Zufrieden)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_RED_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Rot"),
            description=gettext_noop(
                "Beschriftung des roten Betrags (Schmerzgrenze) im Ampel-Gebot."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Rot (Schmerzgrenze)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_PICKUP_LOCATION_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Abholort"),
            description=gettext_noop(
                "Beschriftung der Abholort-Auswahl im Gebotsformular."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Abholort",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LIVE_YEARLY_LABEL,
            label=gettext_noop("Beitragsrunde: Beschriftung Jahresbeitrag"),
            description=gettext_noop(
                "Beschriftung der laufenden Jahresbeitrags-Berechnung im Gebotsformular."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Das ergibt pro Jahr:",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_MONTHLY_HINT,
            label=gettext_noop("Beitragsrunde: Hinweis Monatsbeträge"),
            description=gettext_noop(
                "Hint telling members that all entered amounts are monthly amounts."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Alle Beträge sind Monatsbeträge (€/Monat).",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_MONTHLY_UNIT,
            label=gettext_noop("Beitragsrunde: Einheit Monatsbetrag"),
            description=gettext_noop(
                "Einheit neben den Betragsfeldern, z. B. €/Monat."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="€/Monat",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_CONFIRM_TEXT,
            label=gettext_noop("Beitragsrunde: Bestätigungstext"),
            description=gettext_noop(
                "Text on the confirmation screen before submitting the bid."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Bitte prüfe deine Angaben und bestätige dein Gebot.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_SUCCESS_TEXT,
            label=gettext_noop("Beitragsrunde: Erfolgstext"),
            description=gettext_noop(
                "Text nach dem erfolgreichen Speichern des Gebots."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vielen Dank für dein Gebot! Du erhältst eine Bestätigung per E-Mail.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_ERROR_TEXT,
            label=gettext_noop("Beitragsrunde: Fehlertext"),
            description=gettext_noop(
                "Text bei einem Fehler beim Speichern des Gebots."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein Gebot konnte nicht gespeichert werden. Bitte prüfe deine Eingaben.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )
