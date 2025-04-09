import datetime
from decimal import Decimal
from typing import Dict
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils import timezone
from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.parameters import Parameter


def format_date(value: datetime.date | datetime.datetime) -> str:
    if value is None:
        return ""
    if type(value) is datetime.datetime:
        desired_tz = ZoneInfo("Europe/Berlin")
        localized_datetime = value.astimezone(desired_tz)
        return f"{str(localized_datetime.day).zfill(2)}.{str(localized_datetime.month).zfill(2)}.{localized_datetime.year} {str(localized_datetime.hour).zfill(2)}:{str(localized_datetime.minute).zfill(2)}"
    else:
        return f"{str(value.day).zfill(2)}.{str(value.month).zfill(2)}.{value.year}"


def format_currency(number: int | float | Decimal | str):
    if number is None or number == "":
        return format_currency(0)
    if type(number) is str:
        number = float(number)

    return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def member_detail_url(member_id):
    return reverse_lazy("wirgarten:member_detail", kwargs={"pk": member_id})


def check_permission_or_self(pk, request):
    if not (request.user.pk == pk or request.user.has_perm(Permission.Accounts.MANAGE)):
        raise PermissionDenied


def is_debug_instance():
    return getattr(settings, "DEBUG", False)


def get_today(cache: Dict | None = None) -> datetime.date:
    if is_debug_instance():
        return get_debug_now(cache).date()
    return timezone.localdate()


def get_now(cache: Dict | None = None) -> datetime.datetime:
    if is_debug_instance():
        return get_debug_now(cache)
    return timezone.now()


def get_debug_now(cache: Dict | None = None) -> datetime.datetime:
    date_as_string = get_parameter_value(Parameter.TESTS_OVERRIDE_DATE, cache)
    if date_as_string == "disabled":
        return timezone.now()

    try:
        now = datetime.datetime.fromisoformat(date_as_string)
        return make_timezone_aware(now)
    except ValueError:
        return timezone.now()


def format_subscription_list_html(subs):
    return f"{'<br/>'.join(map(lambda x: '- ' + x.long_str(), subs))}"
