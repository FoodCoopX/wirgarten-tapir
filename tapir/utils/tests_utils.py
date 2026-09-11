from typing import Any
from unittest.mock import Mock

from tapir.utils.shortcuts import get_from_cache_or_compute


def mock_parameter_value(cache: dict, key: str, value: Any):
    parameters_by_key = get_from_cache_or_compute(
        cache=cache, key="parameters_by_key", compute_function=lambda: {}
    )
    tapir_parameter = Mock()
    tapir_parameter.get_value.return_value = value
    parameters_by_key[key] = tapir_parameter
