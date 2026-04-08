from datetime import datetime, date
from decimal import Decimal

from django import template

from tapir.utils.shortcuts import setlocale
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
def format_date(value: date | datetime | str):
    if type(value) is date or type(value) is datetime:
        return utils.format_date(value)
    elif type(value) is str:
        try:
            return utils.format_date(datetime.strptime(value, "%Y-%m-%d").date())
        except ValueError:
            return None
    else:
        return None


@register.filter(name="format_month_and_year")
def format_month_and_year(value: date | datetime) -> str:
    if type(value) is datetime:
        value = value.date()

    with setlocale("de_DE.UTF-8"):
        result = f"{value.strftime("%B")} {value.year}"

    return result


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
