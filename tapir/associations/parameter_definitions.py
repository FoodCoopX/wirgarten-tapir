import typing
from decimal import Decimal

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_association

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import ParameterDefinitions


class ParameterDefinitionsAssociationDeposit:
    @classmethod
    def define_all_parameters_association_deposit(cls, importer: ParameterDefinitions):
        def deposit_increments_enabled(cache: dict) -> bool:
            return association_deposits_enabled(cache) and (
                get_parameter_value(
                    ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, cache=cache
                )
                or get_parameter_value(
                    ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
                )
            )

        def deposit_agreement_enabled(cache: dict) -> bool:
            return association_deposits_enabled(cache) and get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_SIGNUP_WITHOUT_DEPOSIT,
                cache=cache,
            )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED,
            label="Vereinseinlagen aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Zusätzliche rückzahlbare Einlage bei neuen Mitgliedschaften. "
            "Bestehende Vereins- und Erntebeiträge bleiben unabhängig bestehen. "
            "Die Aktivierung erzeugt keine Forderungen für bestehende Mitglieder. "
            "Deaktiviert werden keine neuen Einlagen-Bankdateien erstellt; die Historie bleibt erhalten.",
            category=ParameterCategory.BUSINESS,
            order_priority=-99,
            meta=ParameterMeta(show_only_when=legal_status_is_association),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_NAME,
            label="Name der Vereinseinlage",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vereinseinlage",
            description="Bezeichnung der rückzahlbaren Einlage pro Mitglied. "
            "Die Einlage ist unabhängig von Vereins- und Erntebeiträgen. "
            "Reguläre Einlagen werden über das SEPA-Mandat eingezogen.",
            category=ParameterCategory.BUSINESS,
            order_priority=-100,
            meta=ParameterMeta(show_only_when=association_deposits_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM,
            label="Mindesteinlage pro Mitglied (€)",
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=Decimal("200.00"),
            description="Mindestbetrag der regulären Einlage pro Mitglied, unabhängig "
            "von der Anzahl der Ernteanteile. Eine Erhöhung dieses Wertes löst "
            "keine Nachbelastung bestehender Mitglieder aus.",
            category=ParameterCategory.BUSINESS,
            order_priority=-101,
            meta=ParameterMeta(
                show_only_when=association_deposits_enabled,
                validators=[AssociationDepositAmountValidator.validate_positive_amount],
            ),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT,
            label="Schrittgröße zusätzlicher Einlagen (€)",
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=Decimal("50.00"),
            description="Schrittgröße ab der Mindesteinlage. Bei 200 € Mindestbetrag "
            "und 50 € Schrittgröße sind beispielsweise 200 €, 250 € und 300 € möglich.",
            category=ParameterCategory.BUSINESS,
            order_priority=-102,
            meta=ParameterMeta(
                show_only_when=deposit_increments_enabled,
                validators=[AssociationDepositAmountValidator.validate_positive_amount],
            ),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_MUST_DEPOSIT,
            label="Einlage auch für Fördermitglieder verpflichtend",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Die Mindesteinlage gilt auch bei einer Anmeldung ohne Erntebestellung.",
            category=ParameterCategory.BUSINESS,
            order_priority=-103,
            meta=ParameterMeta(show_only_when=association_deposits_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP,
            label="Höhere Einlage bei der Anmeldung erlauben",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Neue Mitglieder dürfen eine höhere Einlage in den konfigurierten Schritten wählen.",
            category=ParameterCategory.BUSINESS,
            order_priority=-104,
            meta=ParameterMeta(show_only_when=association_deposits_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE,
            label="Einlagenerhöhung im Mitgliederbereich erlauben",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Mitglieder mit vereinbarter Einlage dürfen ihren Gesamtbetrag ausdrücklich erhöhen.",
            category=ParameterCategory.BUSINESS,
            order_priority=-105,
            meta=ParameterMeta(show_only_when=association_deposits_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_SIGNUP_WITHOUT_DEPOSIT,
            label="Anfrage einer individuellen Einlagenvereinbarung erlauben",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Die Anmeldung bleibt ohne vereinbarten Einlagenbetrag und ohne Einzug möglich. Die Anfrage bleibt zur persönlichen Abstimmung sichtbar.",
            category=ParameterCategory.BUSINESS,
            order_priority=-106,
            meta=ParameterMeta(show_only_when=association_deposits_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_SIGNUP_WITHOUT_DEPOSIT_LABEL,
            label="Text der Checkbox für eine individuelle Einlagenvereinbarung",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Ich kann die Mindesteinlage nicht aufbringen und möchte eine individuelle Vereinbarung.",
            description="Text der optionalen Anfrage im Einlagenschritt der Anmeldung.",
            category=ParameterCategory.BUSINESS,
            order_priority=-107,
            meta=ParameterMeta(show_only_when=deposit_agreement_enabled),
        )
