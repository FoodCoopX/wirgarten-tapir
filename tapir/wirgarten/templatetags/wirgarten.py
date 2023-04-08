from datetime import datetime, date
from decimal import Decimal
from zoneinfo import ZoneInfo

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


@register.filter
def remove(value, arg):
    """Removes the specified argument from the input string."""
    value.pop(arg, None)


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
        # Convert the datetime object to the desired timezone
        desired_tz = ZoneInfo("Europe/Berlin")
        localized_datetime = value.astimezone(desired_tz)

        # Format the date and time
        return f"{utils.format_date(localized_datetime)} {str(localized_datetime.hour).zfill(2)}:{str(localized_datetime.minute).zfill(2)}"
    else:
        print(value, type(value), datetime)
        return None


@register.filter(name="format_currency")
def format_currency(value: float | Decimal | int | str):
    return utils.format_currency(value)


@register.filter(name="format_percent")
def format_percent(value: float | Decimal, decimal_places: int = 0):
    display_value = float(value) * 100.0
    return f"{round(display_value) if decimal_places == 0 else round(display_value, decimal_places)} %"
