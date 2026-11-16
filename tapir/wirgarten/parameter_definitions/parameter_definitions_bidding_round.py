import typing

from django.utils.translation import gettext_noop

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import ParameterDefinitions


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
                "Aktiviert nur die mitgliederseitigen Seiten und Endpunkte. Die Admin-Seiten bleiben erreichbar."
            ),
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=9,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TITLE,
            label=gettext_noop("Beitragsrunden-Seite: Titel"),
            description=gettext_noop("Titel der Beitragsrunden-Seite."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Beitragsrunde",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_INTRO_TEXT,
            label=gettext_noop("Beitragsrunden-Seite: Einführungstext"),
            description=gettext_noop("Einführungstext auf der Beitragsrunden-Seite."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="In der Beitragsrunde bestimmst du selbst, wie viel dein Ernteanteil kostet. Mit deinem Beitrag finanzierst du die Saison und sorgst dafür, dass die Solidarität in unserer Gemeinschaft wächst.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_ENDED_TEXT,
            label=gettext_noop(
                "Beitragsrunden-Seite: Text, wenn keine Beitragsrunde aktiv ist"
            ),
            description=gettext_noop(
                "Wird angezeigt, wenn keine Beitragsrunde aktiv ist oder bereits beendet wurde."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value='Die aktuelle Beitragsrunde ist beendet. Du kannst jederzeit Mitglied werden – über unseren <a href="/bestell_wizard/bestell_wizard_mobile">Bestell-Wizard</a> gelangst du direkt zur Anmeldung. Wir freuen uns auf dich!',
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_LOGIN_TITLE,
            label=gettext_noop("Beitragsrunden-Seite: Titel Anmeldung"),
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
            label=gettext_noop("Beitragsrunden-Seite: Text Anmeldung"),
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
            key=ParameterKeys.BIDDING_ROUND_PUBLIC_SUMMARY_TITLE,
            label=gettext_noop("Beitragsrunden-Seite: Titel Gebotsübersicht"),
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
            label=gettext_noop("Beitragsrunden-Seite: Beschriftung Gebot abgeben"),
            description=gettext_noop(
                "Beschriftung der Schaltfläche zum Absenden des Gebots."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Gebot abgeben",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=6,
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
            description=gettext_noop(
                "Hinweis auf den Richtwert im Gebotsformular. Die Variable {reference_value} wird beim Rendern ersetzt."
            ),
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
                "Hinweis, dass alle eingegebenen Beträge Monatsbeträge sind."
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
            key=ParameterKeys.BIDDING_ROUND_BID_YEARLY_UNIT,
            label=gettext_noop("Beitragsrunde: Einheit Jahresbetrag"),
            description=gettext_noop("Einheit neben dem Jahresbetrag, z. B. €/Jahr."),
            datatype=TapirParameterDatatype.STRING,
            initial_value="€/Jahr",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_CONFIRM_TEXT,
            label=gettext_noop("Beitragsrunde: Bestätigungstext"),
            description=gettext_noop(
                "Text auf dem Bestätigungsschritt vor dem Absenden des Gebots."
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
                "Text nach dem erfolgreichen Absenden des Gebots."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Danke! Dein Gebot ist bei uns angekommen. Du kannst es bis zum Ende der Beitragsrunde jederzeit ändern.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )

        importer.parameter_definition(
            key=ParameterKeys.BIDDING_ROUND_BID_ERROR_TEXT,
            label=gettext_noop("Beitragsrunde: Fehlertext"),
            description=gettext_noop(
                "Allgemeiner Fehlertext, wenn das Gebot nicht gespeichert werden konnte."
            ),
            datatype=TapirParameterDatatype.STRING,
            initial_value="Das Gebot konnte nicht gespeichert werden. Bitte prüfe deine Angaben.",
            category=ParameterCategory.BIDDING_ROUND,
            order_priority=5,
            meta=ParameterMeta(textarea=True),
        )
