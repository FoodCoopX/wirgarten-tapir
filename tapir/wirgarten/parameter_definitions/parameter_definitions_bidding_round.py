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
            label=gettext_noop("Enable bidding round"),
            description=gettext_noop(
                "Master switch for the bidding round feature. When disabled, all "
                "bidding round pages are unreachable."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=10,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_URL_ENABLED,
            label=gettext_noop("Enable public bidding round page"),
            description=gettext_noop(
                "Only enables the public bidding round endpoint. The admin pages "
                "remain reachable."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=9,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED,
            label=gettext_noop(
                "Allow changing the pickup location in the bidding round"
            ),
            description=gettext_noop(
                "When enabled, members can change their pickup location while bidding, "
                "as long as the chosen location has free capacity. The member's own "
                "pickup location is always shown."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=8,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_STATS_INCLUDE_AUTO_RENEWED,
            label=gettext_noop(
                "Include automatically renewed members in the evaluation"
            ),
            description=gettext_noop(
                "When enabled, members who did not bid and whose contract is "
                "automatically renewed are included in the evaluation with their "
                "reference value."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_STATS_MEMBERSHIP_INCLUDED_IN_PRODUCT_TYPE,
            label=gettext_noop("Include membership in the harvest share"),
            description=gettext_noop(
                "When enabled, the membership of members with a paid membership is "
                "not charged separately but included in the harvest share (shown in "
                "the harvest shares line instead of as a separate item)."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_NON_BIDDERS_MIN_AVERAGE,
            label=gettext_noop("Non-bidders pay at least the average bid"),
            description=gettext_noop(
                "When enabled, non-bidders (auto-renewers and late joiners) pay at "
                "least the average bid of the bidders. Above-average bids then lead "
                "to a surplus (solidarity fund)."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED,
            label=gettext_noop("Bidding round: show number of shares"),
            description=gettext_noop(
                "When enabled, members can enter the number of shares per item. By "
                "default exactly one share is set."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=7,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
            label=gettext_noop("Public bidding round page: title"),
            description=gettext_noop("Title of the public bidding round page."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Beitragsrunde",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
            label=gettext_noop("Public bidding round page: intro text"),
            description=gettext_noop("Intro text on the public bidding round page."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="In der Beitragsrunde bestimmst du selbst, wie viel dein Ernteanteil kostet. Mit deinem Beitrag finanzierst du die Saison und sorgst dafür, dass die Solidarität in unserer Gemeinschaft wächst.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
            label=gettext_noop(
                "Public bidding round page: text when no bidding round is active"
            ),
            description=gettext_noop(
                "Shown when no bidding round is active or it has already ended. "
                "Registration via the bidding round page is not possible."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value='Die aktuelle Beitragsrunde ist beendet. Du kannst jederzeit Mitglied werden – über unseren <a href="/bestell_wizard/bestell_wizard_mobile">Bestell-Wizard</a> gelangst du direkt zur Anmeldung. Wir freuen uns auf dich!',
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
            label=gettext_noop("Public bidding round page: login title"),
            description=gettext_noop("Title of the login block for existing members."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du bist bereits Mitglied?",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TEXT,
            label=gettext_noop("Public bidding round page: login text"),
            description=gettext_noop("Text of the login block for existing members."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Melde dich an, um dein Gebot abzugeben oder zu ändern.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TITLE,
            label=gettext_noop("Public bidding round page: pickup location title"),
            description=gettext_noop("Title of the pickup location step."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Abholort",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_PICKUP_LOCATION_TEXT,
            label=gettext_noop("Public bidding round page: pickup location text"),
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
            label=gettext_noop("Public bidding round page: bid summary title"),
            description=gettext_noop(
                "Title of the step where the bid is summarized and submitted."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein Gebot",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_SUBMIT_LABEL,
            label=gettext_noop("Public bidding round page: submit bid label"),
            description=gettext_noop("Label of the button that submits the bid."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot abgeben",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TITLE,
            label=gettext_noop("Public bidding round page: progress title"),
            description=gettext_noop(
                "Title of the public progress of the bidding round."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Zwischenstand",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TEXT,
            label=gettext_noop("Public bidding round page: progress text"),
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
            label=gettext_noop("Public bidding round page: progress explanation"),
            description=gettext_noop(
                "Explains in the public progress what utilization, coverage and the "
                "average bid of the bidders mean."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Zwischenstand zeigt, wie die Beitragsrunde gerade steht. „Aktuelle Auslastung“ sagt, wie viele Ernteanteile schon gewünscht sind. „Aktuelle Deckung“ zeigt, wie viel Geld von der Summe, die die Saison kostet, schon zusammenkommt. „Bietende Ø“ ist der durchschnittliche Betrag pro Anteil und Monat, den die Bietenden angeben.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_TRAFFIC_LIGHT_SLIDER_HINT,
            label=gettext_noop("Public bidding round page: traffic light slider hint"),
            description=gettext_noop(
                "Explanation of the solidarity slider in the public evaluation."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Regler zeigt das Solidaritätsniveau von Grün (Wunsch) über Gelb (Zufrieden) bis Rot (Schmerzgrenze). Deckung und Auslastung unten passen sich an.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_STATS_SIMPLE_LEVELS_SLIDER_HINT,
            label=gettext_noop("Public bidding round page: levels slider hint"),
            description=gettext_noop(
                "Explanation of the levels slider in the public evaluation."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Regler wechselt zwischen den Gebotsstufen. Deckung und Auslastung unten passen sich an.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_QUANTITY_LABEL,
            label=gettext_noop("Bidding round: shares label"),
            description=gettext_noop(
                "Label for the number of shares selection in the bid form."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Anzahl Anteile",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_AMOUNT_LABEL,
            label=gettext_noop("Bidding round: amount label"),
            description=gettext_noop("Label for the amount input in the bid form."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein Gebot (€/Monat)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_REFERENCE_VALUE_HINT,
            label=gettext_noop("Bidding round: reference value hint"),
            description=gettext_noop("Available variable: {reference_value}"),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Der Richtwert liegt bei {reference_value} €/Monat.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(vars_hint=["reference_value"]),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_SIMPLE_EXPLANATION,
            label=gettext_noop("Bidding round: simple bid explanation"),
            description=gettext_noop(
                "Explanation text for the simple bid (one amount)."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Du gibst einen Betrag an: So viel möchtest du pro Monat für deinen Ernteanteil zahlen. Der Betrag gilt für die ganze Saison.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_TRAFFIC_LIGHT_EXPLANATION,
            label=gettext_noop("Bidding round: traffic light bid explanation"),
            description=gettext_noop(
                "Explanation text for the traffic light bid (three amounts)."
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
                "Bidding round: simple bid explanation (multiple levels)"
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
            label=gettext_noop("Bidding round: level 1 label"),
            description=gettext_noop("Label of the first bid level in the simple bid."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot 1",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LEVEL_2_LABEL,
            label=gettext_noop("Bidding round: level 2 label"),
            description=gettext_noop(
                "Label of the second bid level in the simple bid."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot 2",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LEVEL_3_LABEL,
            label=gettext_noop("Bidding round: level 3 label"),
            description=gettext_noop("Label of the third bid level in the simple bid."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot 3",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_GREEN_LABEL,
            label=gettext_noop("Bidding round: green label"),
            description=gettext_noop(
                "Label of the green amount (wish) in the traffic light bid."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Grün (Wunsch)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_YELLOW_LABEL,
            label=gettext_noop("Bidding round: yellow label"),
            description=gettext_noop(
                "Label of the yellow amount (satisfied) in the traffic light bid."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gelb (Zufrieden)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_RED_LABEL,
            label=gettext_noop("Bidding round: red label"),
            description=gettext_noop(
                "Label of the red amount (pain threshold) in the traffic light bid."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Rot (Schmerzgrenze)",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_PICKUP_LOCATION_LABEL,
            label=gettext_noop("Bidding round: pickup location label"),
            description=gettext_noop(
                "Label of the pickup location selection in the bid form."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Abholort",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_LIVE_YEARLY_LABEL,
            label=gettext_noop("Bidding round: yearly contribution label"),
            description=gettext_noop(
                "Label for the live yearly contribution calculation in the bid form."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Das ergibt pro Jahr:",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_MONTHLY_HINT,
            label=gettext_noop("Bidding round: monthly amounts hint"),
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
            label=gettext_noop("Bidding round: monthly unit"),
            description=gettext_noop(
                "Unit shown next to the amount input fields, e.g. €/Monat."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="€/Monat",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_CONFIRM_TEXT,
            label=gettext_noop("Bidding round: confirmation text"),
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
            label=gettext_noop("Bidding round: success text"),
            description=gettext_noop("Text after the bid has been saved successfully."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vielen Dank für dein Gebot! Du erhältst eine Bestätigung per E-Mail.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_ERROR_TEXT,
            label=gettext_noop("Bidding round: error text"),
            description=gettext_noop("Text on an error while saving the bid."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Dein Gebot konnte nicht gespeichert werden. Bitte prüfe deine Eingaben.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )
