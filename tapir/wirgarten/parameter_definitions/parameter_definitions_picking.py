import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.pickup_locations.config import PICKING_MODE_SHARE, OPTIONS_PICKING_MODE
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsPicking:
    @classmethod
    def define_all_parameters_picking(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.PICKING_PRODUCT_TYPES,
            label="Produkttypen für Kommisionierliste",
            datatype=TapirParameterDatatype.STRING,
            initial_value="alle",
            description="Komma-separierte Liste der Produkttypen für die eine Kommissionierliste erzeugt werden soll. Oder 'alle' um für alle Produkttypen eine Kommissionierliste zu erzeugen.",
            category=ParameterCategory.PICKING,
            order_priority=4,
        )

        importer.parameter_definition(
            key=ParameterKeys.PICKING_SEND_ADMIN_EMAIL,
            label="Automatische Email an Admin",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn aktiv, dann wird automatisch wöchentlich eine Email mit der Kommisionierliste an den Admin versandt.",
            category=ParameterCategory.PICKING,
            order_priority=5,
        )

        importer.parameter_definition(
            key=ParameterKeys.PICKING_MODE,
            label="Kommissionierungsmodus",
            datatype=TapirParameterDatatype.STRING,
            initial_value=PICKING_MODE_SHARE,
            description="Ob Verteilstation-Kapazitäten nach Anteile oder Kisten berechnet werden",
            category=ParameterCategory.PICKING,
            order_priority=3,
            meta=ParameterMeta(options=OPTIONS_PICKING_MODE),
            enabled=is_debug_instance(),
        )

        importer.parameter_definition(
            key=ParameterKeys.PICKING_BASKET_SIZES,
            label="Kistengrößen",
            datatype=TapirParameterDatatype.STRING,
            initial_value="kleine Kiste;normale Kiste;",
            description="Nur relevant beim Kommissionierungsmodus nach Kisten. Liste der Kistengrößen, mit ';' getrennt. Beispiel: 'kleine Kiste;normale Kiste;'",
            category=ParameterCategory.PICKING,
            order_priority=2,
            meta=ParameterMeta(
                validators=[BasketSizeCapacitiesService.validate_basket_sizes]
            ),
        )
