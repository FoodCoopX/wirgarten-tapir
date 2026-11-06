import typing
from decimal import Decimal

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_association

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import ParameterDefinitions


class ParameterDefinitionsAssociationDeposit:
    @classmethod
    def define_all_parameters_association_deposit(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.ASSOCIATION_DEPOSIT_NAME,
            label="Name der Vereinseinlage",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Vereinseinlage",
            description="Bezeichnung der rückzahlbaren Einlage pro Mitglied. "
            "Die Einlage ist unabhängig von Vereins- und Erntebeiträgen. "
            "Diese Einstellungen lösen noch keine Einlagenzahlungen aus.",
            category=ParameterCategory.BUSINESS,
            order_priority=-100,
            meta=ParameterMeta(show_only_when=legal_status_is_association),
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
                show_only_when=legal_status_is_association,
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
                show_only_when=legal_status_is_association,
                validators=[AssociationDepositAmountValidator.validate_positive_amount],
            ),
        )
