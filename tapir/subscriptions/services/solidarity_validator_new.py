import datetime

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions import config
from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.wirgarten.parameter_keys import ParameterKeys


class SolidarityValidatorNew:
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
                excess_solidarity = SolidarityValidator.get_solidarity_excess(
                    reference_date=start_date, cache=cache
                )
                amount_of_used_solidarity_in_euros = -ordered_solidarity_factor
                return amount_of_used_solidarity_in_euros > excess_solidarity
            case _:
                raise ImproperlyConfigured(
                    f"Unknown solidarity mode: '{solidarity_mode}'"
                )
