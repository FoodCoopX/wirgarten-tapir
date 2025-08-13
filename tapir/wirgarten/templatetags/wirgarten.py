from datetime import datetime, date
from decimal import Decimal

from django import template

from tapir.wirgarten import utils
from tapir.wirgarten.utils import get_now

register = template.Library()


@register.filter(name="get_value")
def get_value(dictionary, key):
    if type(dictionary) is dict:
        return dictionary.get(key)
    else:
        return None


@register.filter
def remove(value, arg):
    """Removes the specified argument from the input string."""
    value.pop(arg, None)


@register.filter(name="format_date")
def format_date(value: date | datetime):
    if type(value) is date or type(value) is datetime:
        return utils.format_date(value)
    else:
        return None


@register.filter(name="format_currency")
def format_currency(value: float | Decimal | int | str):
    return utils.format_currency(value)


@register.filter(name="format_percent")
def format_percent(value: float | Decimal, decimal_places: int = 0):
    display_value = float(value) * 100.0
    return f"{round(display_value) if decimal_places == 0 else round(display_value, decimal_places)} %"


@register.simple_tag
def create_range(n):
    return range(n)


@register.simple_tag()
def get_now_tag(cache):
    if not isinstance(cache, dict):
        cache = None
    return format_date(get_now(cache=cache))
