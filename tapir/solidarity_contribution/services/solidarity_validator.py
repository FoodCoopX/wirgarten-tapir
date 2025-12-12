import datetime
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured, ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions import config
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
    SOLIDARITY_MODE_ONLY_POSITIVE,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.parameter_keys import ParameterKeys


class SolidarityValidator:
    @classmethod
    def is_the_ordered_solidarity_allowed(
        cls,
        ordered_solidarity_factor: float,
        start_date: datetime.date,
        cache: dict,
    ) -> bool:
        if ordered_solidarity_factor >= 0:
            return True

        solidarity_mode = get_parameter_value(
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        match solidarity_mode:
            case config.SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED:
                return True
            case config.SOLIDARITY_MODE_ONLY_POSITIVE:
                return False
            case config.SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE:
                excess_solidarity = cls.get_solidarity_excess(
                    reference_date=start_date, cache=cache
                )
                amount_of_used_solidarity_in_euros = -ordered_solidarity_factor
                return amount_of_used_solidarity_in_euros < excess_solidarity
            case _:
                raise ImproperlyConfigured(
                    f"Unknown solidarity mode: '{solidarity_mode}'"
                )

    @classmethod
    def get_solidarity_excess(
        cls,
        reference_date: datetime.date,
        cache: dict,
    ) -> Decimal:
        return TapirCache.get_solidarity_excess_at_date(
            reference_date=reference_date, cache=cache
        )

    @classmethod
    def get_solidarity_contribution_minimum(
        cls, reference_date: datetime.date, cache: dict
    ) -> float | None:
        enabled = get_parameter_value(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        if enabled == SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED:
            return None
        if enabled == SOLIDARITY_MODE_ONLY_POSITIVE:
            return 0.0

        return min(
            0.0,
            -float(
                cls.get_solidarity_excess(
                    reference_date=reference_date, cache=cache
                ).quantize(Decimal("0.01"))
            ),
        )

    @classmethod
    def get_solidarity_dropdown_values(
        cls, parameter_value: str = None, cache: dict = None
    ):
        if parameter_value is None:
            parameter_value = get_parameter_value(
                ParameterKeys.SOLIDARITY_CHOICES, cache=cache
            )

        values_as_string = parameter_value.split(",")
        values: list[float | str] = [float(value.strip()) for value in values_as_string]

        if 0 not in values:
            values.append(0)

        if "custom" not in values:
            values.append("custom")

        return {value: cls.get_value_display(value=value) for value in values}

    @classmethod
    def get_value_display(cls, value):
        if value == 0:
            return "0€"
        if value == "custom":
            return "Ich möchte einen anderen Betrag zahlen"

        return f"{value:+g}€"

    @classmethod
    def validate_solidarity_dropdown_values(cls, solidarity_values_as_string: str):
        try:
            cls.get_solidarity_dropdown_values(solidarity_values_as_string, cache={})
        except Exception as e:
            raise ValidationError(f"Invalid solidarity values: {e}")
