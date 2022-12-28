from datetime import datetime, date
from decimal import Decimal

from django import template

from tapir.wirgarten import utils
from tapir.wirgarten.views import FORM_TITLES

register = template.Library()


@register.filter(name="get_value")
def get_value(dictionary, key):
    if type(dictionary) is dict:
        return dictionary.get(key)
    else:
        return None


@register.filter(name="get_step_title")
def get_step_title(step):
    return FORM_TITLES.get(step, step)


@register.inclusion_tag(
    "wirgarten/registration/steps/components/summary_card_disabled.html"
)
def summary_card_disabled(title):
    return {"title": title}


@register.filter(name="format_date")
def format_date(value: date | datetime):
    if type(value) is date:
        return utils.format_date(value)
    elif type(value) is datetime:
        return f"{utils.format_date(value)}, {str(value.hour).zfill(2)}:{str(value.minute).zfill(2)}"
    else:
        return None


@register.filter(name="format_currency")
def format_currency(value: float | Decimal | int):
    return utils.format_currency(value)


@register.filter(name="format_percent")
def format_percent(value: float | Decimal, decimal_places: int = 0):
    display_value = float(value) * 100.0
    return f"{round(display_value) if decimal_places == 0 else round(display_value, decimal_places)} %"
