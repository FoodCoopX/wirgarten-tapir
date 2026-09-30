import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsBakery:
    @classmethod
    def define_all_parameters_bakery(cls, importer: "ParameterDefinitions"):

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_ENABLED,
            label="Bäckerei-Funktion aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Aktiviert die Bäckerei-Funktionalität für Brotbestellungen",
            category=ParameterCategory.BAKERY,
            order_priority=10,
        )

        def bakery_enabled(cache):
            from tapir.configuration.parameter import get_parameter_value

            return get_parameter_value(ParameterKeys.BAKERY_ENABLED, cache)

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_STOVE_LAYERS,
            label="Anzahl der Backofen-Etagen",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=3,
            description="Gibt an, wie viele Etagen der Backofen hat.",
            category=ParameterCategory.BAKERY,
            order_priority=1,
            meta=ParameterMeta(show_only_when=bakery_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_BAKING_DAY_BEFORE_DELIVERY_DAY,
            label="Backtag vor Liefertag",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=1,
            description="Gibt an, wie viele Tage vor dem Liefertag der Backtag liegt.",
            category=ParameterCategory.BAKERY,
            order_priority=2,
            meta=ParameterMeta(show_only_when=bakery_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_LAST_CHOOSING_DAY_BEFORE_BAKING_DAY,
            label="Letzter Brot-Auswahltag vor Backtag",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Gibt an, wie viele Tage vor dem Backtag der letzte Auswahltag liegt.",
            category=ParameterCategory.BAKERY,
            order_priority=3,
            meta=ParameterMeta(show_only_when=bakery_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_REDUCE_BREAD_SHARES,
            label="Mitglieder können Brotanteile reduzieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Gibt an, ob Mitglieder ihre Brotanteile reduzieren können.",
            category=ParameterCategory.BAKERY,
            order_priority=7,
            meta=ParameterMeta(show_only_when=bakery_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS,
            label="Mitglieder können Brotsorten wählen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Gibt an, ob Mitglieder ihre Brotsorten wählen können.",
            category=ParameterCategory.BAKERY,
            order_priority=6,
            meta=ParameterMeta(show_only_when=bakery_enabled),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_PICKUP_LOCATIONS_CAN_BE_CHOSEN_PER_SHARE,
            label="Mitglieder können Abholstationen pro Anteil wählen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Gibt an, ob Mitglieder Abholstationen pro Brotanteil wählen können.",
            category=ParameterCategory.BAKERY,
            order_priority=5,
            meta=ParameterMeta(show_only_when=bakery_enabled),
        )
