import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory, OPTIONS_WEEKDAYS
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsDelivery:
    @classmethod
    def define_all_parameters_delivery(cls, importer: ParameterDefinitions):
        order_priority = 100

        importer.parameter_definition(
            key=ParameterKeys.DELIVERY_DAY,
            label="Wochentag an dem Ware geliefert wird",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Der Wochentag an dem die Ware zum Abholort geliefert wird.",
            category=ParameterCategory.DELIVERY,
            meta=ParameterMeta(options=OPTIONS_WEEKDAYS),
            order_priority=order_priority,
        )
        order_priority -= 1

        importer.parameter_definition(
            key=ParameterKeys.DELIVERY_CHARGE_PER_PICKUP_LOCATION_ENABLED,
            label="Lieferzuschlag pro Verteilstation aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn aktiviert können auf der Abholort-Konfig-Seite Lieferzuschläge definiert werden.",
            category=ParameterCategory.DELIVERY,
            order_priority=order_priority,
        )
        order_priority -= 1
