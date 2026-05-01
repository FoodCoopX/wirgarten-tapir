import datetime
import typing

from django.core.validators import MinValueValidator, MaxValueValidator

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.payments.services.mandate_reference_pattern_validator import (
    MandateReferencePatternValidator,
)
from tapir.payments.config import IntendedUseTokens
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_cooperative

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )

WARNING_USE_EDITOR = "Es ist empfohlen dieses Parameter nicht direkt zu ändern sondern den Editor zu nutzen, nutz dafür den Knopf am Textfeld Rechts"


class ParameterDefinitionsPayments:
    @classmethod
    def define_all_parameters_payments(cls, importer: ParameterDefinitions):
        from tapir.wirgarten.validators import validate_date_is_first_of_month
        from tapir.payments.models import MemberPaymentRhythm
        from tapir.payments.services.member_payment_rhythm_service import (
            MemberPaymentRhythmService,
        )

        order_priority = 100

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_DUE_DAY,
            label="Fälligkeitsdatum der Beitragszahlungen (Tag des Monats)",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=15,
            description="Der Tag im Monat an dem Beitragszahlungen für Abonnements fällig sind.",
            category=ParameterCategory.PAYMENT,
            meta=ParameterMeta(
                validators=[
                    MinValueValidator(limit_value=1),
                    MaxValueValidator(limit_value=31),
                ]
            ),
            enabled=is_debug_instance(),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM,
            label="Standard Zahlungsintervall.",
            datatype=TapirParameterDatatype.STRING,
            initial_value=MemberPaymentRhythm.Rhythm.MONTHLY,
            description="Zahlungsintervall das vorausgewählt ist im BestellWizard.",
            category=ParameterCategory.PAYMENT,
            meta=ParameterMeta(
                options_callable=lambda cache: [
                    (rhythm, MemberPaymentRhythmService.get_rhythm_display_name(rhythm))
                    for rhythm in MemberPaymentRhythmService.get_allowed_rhythms(
                        cache=cache
                    )
                ]
            ),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_ALLOWED_RHYTHMS,
            label="Erlaubte Zahlungsintervalle.",
            datatype=TapirParameterDatatype.STRING,
            initial_value=", ".join(
                [str(choice[1]) for choice in MemberPaymentRhythm.Rhythm.choices]
            ),
            description="Zahlungsintervalle die ausgewählt werden können, als Komma-getrennte liste. Beispiel: 'Monatlich, Vierteljährlich, Halbjährlich, Jährlich'.",
            category=ParameterCategory.PAYMENT,
            meta=ParameterMeta(
                validators=[MemberPaymentRhythmService.validate_rhythms]
            ),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_START_DATE,
            label="Start-Datum für die Zahlungen",
            datatype=TapirParameterDatatype.DATE,
            initial_value=datetime.date.today().replace(day=1),
            description="Ab welche Datum sollen Zahlungen eingezogen werden. Es ist relevant wenn Verträge in Tapir importiert werden wo außerhalb von Tapir Zahlungen schon eingezogen sind.",
            category=ParameterCategory.PAYMENT,
            meta=ParameterMeta(validators=[validate_date_is_first_of_month]),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_ORGANISATION_IBAN,
            label="IBAN der Organisation",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="Wird im Export der Lastschriften oben eingefügt, da für Umwandlung in XML-Datei notwendig.",
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER,
            label="Gläubiger-Identifikationsnummer",
            datatype=TapirParameterDatatype.STRING,
            initial_value="",
            description="Wird im Export der Lastschriften oben eingefügt, da für Umwandlung in XML-Datei notwendig.",
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_MANDATE_REFERENCE_PATTERN,
            label="Mandatsreferenz-Muster",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{nachname}{vorname}/{zufall}",
            description="Nach welchem Muster die Mandatsreferenz generiert werden soll. <br /> "
            "Damit es immer einzigartig ist müssen mindestens einer dieser Token verwendet werden: {mitgliedsnummer_kurz}, {mitgliedsnummer_lang}, {mitgliedsnummer_ohne_prefix}, {zufall}. <br />"
            "Die Tokens {vorname} und {nachname} nehmen jeweils nur die erste 5 Buchstaben. <br />"
            "Soll dieses Parameter geändert werden, bleiben bestehende Mandatsreferenzen unverändert.",
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
            meta=ParameterMeta(
                vars_hint=[
                    MandateReferencePatternValidator.TOKEN_FIRST_NAME,
                    MandateReferencePatternValidator.TOKEN_LAST_NAME,
                    MandateReferencePatternValidator.TOKEN_MEMBER_NUMBER_SHORT,
                    MandateReferencePatternValidator.TOKEN_MEMBER_NUMBER_LONG,
                    MandateReferencePatternValidator.TOKEN_MEMBER_NUMBER_WITHOUT_PREFIX,
                    MandateReferencePatternValidator.TOKEN_RANDOM,
                ],
                validators=[MandateReferencePatternValidator.validate_pattern],
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM,
            label="Personalisierte Verwendungszwecke aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="",
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_INTENDED_USE_COOP_SHARES,
            label="Verwendungszweck für Genoanteilsbuchungen",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{betriebsname}, {anzahl_geno_anteile} GenoAnteile\n{nachname} {mitgliedsnummer_lang}\nBeitritt: {beitrittsdatum}",
            description=WARNING_USE_EDITOR,
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, cache=cache
                )
                and legal_status_is_cooperative(cache=cache),
                textarea=True,
                vars_hint=IntendedUseTokens.COMMON_TOKENS
                + IntendedUseTokens.COOP_SHARE_TOKENS,
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE,
            label="Verwendungszweck für Beitragsabbuchungen regulär",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{betriebsname}\n{nachname} {mitgliedsnummer_lang}\n{vertragsliste}",
            description=WARNING_USE_EDITOR,
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, cache=cache
                ),
                textarea=True,
                vars_hint=IntendedUseTokens.COMMON_TOKENS
                + IntendedUseTokens.CONTRACT_TOKENS,
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE_SOLIDARITY_SUPPORTED,
            label="Verwendungszweck für Beitragsabbuchungen solidarisch finanziert",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{betriebsname}\n{nachname} {mitgliedsnummer_lang}\n{vertragsliste}\nBeitrag solid.finanziert",
            description=WARNING_USE_EDITOR,
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, cache=cache
                ),
                textarea=True,
                vars_hint=IntendedUseTokens.COMMON_TOKENS
                + IntendedUseTokens.CONTRACT_TOKENS,
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_INTENDED_USE_SOLI_CONTRIBUTION_ONLY,
            label="Verwendungszweck für Beitragsabbuchungen wenn Fördermitglied",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{betriebsname}\n{nachname} {mitgliedsnummer_lang}\nSolidarbeitrag",
            description=WARNING_USE_EDITOR,
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, cache=cache
                ),
                textarea=True,
                vars_hint=IntendedUseTokens.COMMON_TOKENS
                + IntendedUseTokens.CONTRACT_TOKENS,
            ),
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.PAYMENT_INTENDED_USE_MULTIPLE_MONTH_INVOICE,
            label="Verwendungszweck für Beitragsabbuchungen erstmalig",
            datatype=TapirParameterDatatype.STRING,
            initial_value="{betriebsname}\n{nachname} {mitgliedsnummer_lang}\n{vertragsliste}\nSonderbeitrag",
            description="Wird verwendet typischerweise in der Probezeit, wenn eine Buchung mehr Monate abdeckt als normal. "
            + WARNING_USE_EDITOR,
            category=ParameterCategory.PAYMENT,
            order_priority=order_priority,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, cache=cache
                ),
                textarea=True,
                vars_hint=IntendedUseTokens.COMMON_TOKENS
                + IntendedUseTokens.CONTRACT_TOKENS,
            ),
        )
        order_priority -= 1
