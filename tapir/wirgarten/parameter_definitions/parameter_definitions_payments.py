import datetime
import typing

from django.core.validators import MinValueValidator, MaxValueValidator

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


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
