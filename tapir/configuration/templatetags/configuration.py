from typing import Dict

from django import template
from django.template.defaultfilters import stringfilter

from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import LEGAL_STATUS_OPTIONS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import format_date, get_now

register = template.Library()


@register.filter(name="parameter")
@stringfilter
def parameter_value(key: str):
    try:
        return get_parameter_value(key)
    except KeyError:
        return None


@register.simple_tag()
def get_parameter_value_tag(key: str, cache):
    if not isinstance(cache, dict):
        cache = None
    return get_parameter_value(key, cache=cache)


@register.simple_tag
def tokenize_parameter(text: str, cache: Dict = None):
    legal_status = "Betrieb"
    for status in LEGAL_STATUS_OPTIONS:
        if status[0] == get_parameter_value(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache
        ):
            legal_status = status[1]
            break

    tokens = {"legal_status": legal_status, "now": format_date(get_now(cache=cache))}

    for token, value in tokens.items():
        text = text.replace("{{" + token + "}}", value)

    return text
