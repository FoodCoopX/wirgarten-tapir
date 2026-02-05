import typing
from decimal import Decimal

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
    SOLIDARITY_MODE_OPTIONS,
)
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsSolidarity:
    @classmethod
    def define_all_parameters_solidarity(cls, importer: ParameterDefinitions):
        from tapir.solidarity_contribution.services.solidarity_validator import (
            SolidarityValidator,
        )

        order_priority = 100

        importer.parameter_definition(
            key=ParameterKeys.SOLIDARITY_CHOICES,
            label="Vordefinierte Solidarbeitrag-Werten",
            datatype=TapirParameterDatatype.STRING,
            initial_value="-15,-10,-5,0,5,10,15",
            description="Komma-getrennte Liste der Werte die beim Solidarbeitrag zu auswahl stehen."
            "Es gibt immer dazu für das Mitglied die Möglichkeit eine andere Wert anzugeben."
            "Beispiel: '-15,-10,-5,0,5,10,15'"
            "Je nach dem was im Feld 'Einheit des Solidarbeitrag' eingetragen ist sind die Werte Prozente (5%, 10%, ...) oder Euros (5€, 10€,...)",
            category=ParameterCategory.SOLIDARITY,
            meta=ParameterMeta(
                validators=[SolidarityValidator.validate_solidarity_dropdown_values]
            ),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.SOLIDARITY_DEFAULT,
            label="Vorausgewählter Beitrag im Bestell Wizard",
            datatype=TapirParameterDatatype.DECIMAL,
            initial_value=Decimal(0),
            description="Welche Wert vorausgewählt ist im Bestell Wizard. Kann ein andere Wert sein als die vordefinierte. Kann vom Mitglied geändert werden.",
            category=ParameterCategory.SOLIDARITY,
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED,
            label="Solidarpreise möglich",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE,
            description="Aktiviert oder deaktiviert niedrigere Preise für Ernteanteile oder aktiviert die automatische Berechnung.",
            category=ParameterCategory.SOLIDARITY,
            meta=ParameterMeta(options=SOLIDARITY_MODE_OPTIONS),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE,
            label="Mitglieder dürfen der Solibeitrag laufend ändern",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn aktiviert, Mitglieder dürfen deren Solibeitrag ändern auch während ein Vertrag läuft. "
            "Wenn ausgeschaltet, Mitglieder dürfen deren Solibeitrag nur ändern wenn sie einen neuen Vertrag abschliessen.",
            category=ParameterCategory.SOLIDARITY,
            order_priority=order_priority,
        )
        order_priority -= 1
