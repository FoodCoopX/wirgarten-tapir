import typing

from tapir.configuration.models import TapirParameterDatatype
from tapir.configuration.parameter import ParameterMeta, get_parameter_value
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys

if typing.TYPE_CHECKING:
    from tapir.wirgarten.parameters import (
        ParameterDefinitions,
    )


class ParameterDefinitionsTrialPeriod:
    @classmethod
    def define_all_parameters_trial_period(cls, importer: ParameterDefinitions):
        importer.parameter_definition(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED,
            label="Probezeit einschalten",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Ob Verträge eine Probezeit haben in dem früher gekündigt werden kann.",
            category=ParameterCategory.TRIAL_PERIOD,
            order_priority=100,
            enabled=is_debug_instance(),
        )

        importer.parameter_definition(
            key=ParameterKeys.TRIAL_PERIOD_DURATION,
            label="Probezeit in Wochen",
            datatype=TapirParameterDatatype.INTEGER,
            initial_value=4,
            description="Länge der Probezeit in Wochen.",
            category=ParameterCategory.TRIAL_PERIOD,
            order_priority=90,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
                ),
            ),
            enabled=is_debug_instance(),
        )

        importer.parameter_definition(
            key=ParameterKeys.TRIAL_PERIOD_CAN_BE_CANCELLED_BEFORE_END,
            label="Probezeit kann flexibel gekündigt werden.",
            datatype=TapirParameterDatatype.BOOLEAN,
            initial_value=True,
            description="Wenn an, ist es möglich während der Probezeit zu kündigen. Wenn aus, die Probezeit muss ganz benutzt werden.",
            category=ParameterCategory.TRIAL_PERIOD,
            order_priority=80,
            meta=ParameterMeta(
                show_only_when=lambda cache: get_parameter_value(
                    ParameterKeys.TRIAL_PERIOD_ENABLED, cache=cache
                ),
            ),
        )
