import datetime
import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.subscriptions.config import (
    NOTICE_PERIOD_UNIT_MONTHS,
    NOTICE_PERIOD_UNIT_OPTIONS,
)
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsSubscriptions:
    @classmethod
    def define_all_parameters_subscriptions(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL,
            label="Automatische Verlängerung der Verträge",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=3,
            enabled=is_debug_instance(),
        )

        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD,
            label="Kündigungsfrist",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=2,
            description="Bei automatischer Verlängerung der Verträge",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=2,
            enabled=is_debug_instance(),
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
                )
            ),
        )

        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD_UNIT,
            label="Einheit der Kündigungsfrist",
            datatype=TapirParameterDatatype.STRING,
            initial_value=NOTICE_PERIOD_UNIT_MONTHS,
            description="Ob der Feld Kündigungsfrist Monate oder Wochen angibt",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=1,
            meta=ParameterMeta(
                options=NOTICE_PERIOD_UNIT_OPTIONS,
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
                ),
            ),
            enabled=is_debug_instance(),
        )

        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            label="Zusatzproduktverträge erlauben ohne Basisproduktvertrag",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=False,
            description="Wenn dieses Feld aus ist, können Zusatzproduktverträge nur gezeichnet werden "
            "wenn das Mitglied mindestens ein Basisproduktvertrag gezeichnet hat.",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=0,
        )

        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES,
            label="Warteliste-Kategorien",
            datatype=TapirParameterDatatype.STRING,
            initial_value="Kategorie 1, Kategorie 2, Kategorie 3",
            description="Kategorien die in an Einträge der Warteliste zugewiesen werden können. Format: Kategorien-Namen mit ',' separiert. Anzahl beliebig",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=1,
        )

        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_FOUR_WEEK_CYCLE_START_POINT,
            label="Startpunkt der 4-Wochigen Lieferrhythmus",
            datatype=TapirParameterDatatype.DATE,
            initial_value=datetime.date(year=2025, month=1, day=6),
            description="Erste Woche die geliefert wird für Produkte die der 4-Wochigen Lieferrhythmus folgen.",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=1,
        )

        importer.parameter_definition(
            key=ParameterKeys.ENABLE_GROWING_PERIOD_CHOICE_DAYS_BEFORE,
            label="Schwelle zu Vertragsperiode-Auswahl",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=61,
            description="Wie viele Tage vor eine neue Vertragsperiode wird der Auswahl angezeigt im Bestellwizard in welche Vertragsperiode der Vertrags gültig ist.",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=0,
        )

        importer.parameter_definition(
            key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START,
            label="Vorlaufzeit zu Vertragsstart",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=0,
            description="Gibt an, wie viele Tage vor der Kommissionierungsvariable der Vertrag gezeichnet werden muss, um noch in der nächsten Woche zu starten.",
            category=ParameterCategory.SUBSCRIPTIONS,
            order_priority=2,
        )
