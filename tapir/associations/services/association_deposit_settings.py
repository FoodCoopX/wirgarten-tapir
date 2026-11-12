from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_association


def association_deposits_enabled(cache: dict) -> bool:
    return legal_status_is_association(cache=cache) and get_parameter_value(
        ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, cache=cache
    )
