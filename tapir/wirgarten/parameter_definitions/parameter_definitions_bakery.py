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
    def define_all_parameters_bakery(cls, importer: ParameterDefinitions):

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_ENABLED,
            label="Bäckerei-Funktion aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Aktiviert die Bäckerei-Funktionalität für Brotbestellungen",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_PSEUDONYM_ENABLED,
            label="Pseudonym-Funktion für Bäckerei aktivieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Aktiviert die Möglichkeit, dass Mitglieder für Brotbestellungen ein Pseudonym angeben können, anstatt ihren echten Namen zu verwenden.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_BAKING_DAY_BEFORE_DELIVERY_DAY,
            label="Backtag vor Liefertag",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=1,
            description="Gibt an, wie viele Tage vor dem Liefertag der Backtag liegt. Zum Beispiel, wenn der Liefertag am Mittwoch ist und dieser Parameter auf 1 gesetzt ist, dann ist der Backtag am Dienstag.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )

        importer.parameter_definition(
            key=ParameterKeys.BAKERY_LAST_CHOOSING_DAY_BEFORE_BAKING_DAY,
            label="Letzter Brot-Auswahltag vor Backtag",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Gibt an, wie viele Tage vor dem Backtag der letzte Auswahltag liegt. Zum Beispiel, wenn der Backtag am Dienstag ist und dieser Parameter auf 2 gesetzt ist, dann ist der letzte Auswahltag am Sonntag.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )
        importer.parameter_definition(
            key=ParameterKeys.BAKERY_DAYS_BEFORE_DELIVERY_DAY_TO_CHANGE_PSEUDONYM,
            label="Tage vor Liefertag, um Pseudonym zu ändern",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=1,
            description="Gibt an, wie viele Tage vor dem Liefertag ein Mitglied sein Pseudonym ändern kann.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )
        importer.parameter_definition(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_REDUCES_BREAD_SHARES,
            label="Mitglieder können Brotanteile reduzieren",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Gibt an, ob Mitglieder ihre Brotanteile reduzieren können.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )
        importer.parameter_definition(
            key=ParameterKeys.BAKERY_PICKUP_LOCATIONS_CAN_BE_CHOSEN_PER_SHARE,
            label="Mitglieder können Abholstationen pro Anteil wählen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Gibt an, ob Mitglieder ihre Abholstationen pro Brotanteil wählen können.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )
        importer.parameter_definition(
            key=ParameterKeys.BAKERY_PICKUP_LOCATIONS_CAN_BE_ORDERED_BY_DAYS_IN_BESTELL_WIZARD,
            label="Abholstationen können im BestellWizard nach Tagen sortiert werden",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Gibt an, ob die Abholstationen im BestellWizard nach Tagen sortiert werden können.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )
        importer.parameter_definition(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS,
            label="Mitglieder können Brotsorten wählen",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Gibt an, ob Mitglieder ihre Brotsorten wählen können.",
            category=ParameterCategory.BAKERY,
            meta=ParameterMeta(),
        )
