import datetime
import logging
from decimal import Decimal
from typing import Dict
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils import timezone

from tapir.configuration.parameter import get_parameter_value
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_ASSOCIATION,
    TEST_DATE_OVERRIDE_DISABLED,
    TEST_DATE_OVERRIDE_MANUAL,
    TEST_DATE_OVERRIDE_FIRST_DAY_THIS_YEAR,
    TEST_DATE_OVERRIDE_OCTOBER_TENTH_THIS_YEAR,
    TEST_DATE_OVERRIDE_DECEMBER_FIFTEENTH_THIS_YEAR,
    TEST_DATE_OVERRIDE_LAST_MINUTE_OF_THIS_YEAR,
    TEST_DATE_OVERRIDE_END_OF_FIRST_DAY_NEXT_YEAR,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.is_debug_instance import is_debug_instance
from tapir.wirgarten.parameter_keys import ParameterKeys

LOG = logging.getLogger(__name__)


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


def get_today(cache: Dict | None = None) -> datetime.date:
    if is_debug_instance():
        return get_debug_now(cache).date()
    return timezone.localdate()


def get_now(cache: Dict | None = None) -> datetime.datetime:
    if is_debug_instance():
        return get_debug_now(cache)
    return timezone.now()


def get_debug_now(cache: Dict | None = None) -> datetime.datetime:
    preset = get_parameter_value(ParameterKeys.TESTS_OVERRIDE_DATE_PRESET, cache=cache)

    if preset == TEST_DATE_OVERRIDE_DISABLED:
        return timezone.now()

    tzinfo = ZoneInfo("Europe/Berlin")

    if preset == TEST_DATE_OVERRIDE_MANUAL:
        date_as_string = get_parameter_value(
            ParameterKeys.TESTS_OVERRIDE_DATE, cache=cache
        )
        try:
            return datetime.datetime.fromisoformat(date_as_string).replace(
                tzinfo=tzinfo
            )
        except ValueError:
            return timezone.now()

    if preset == TEST_DATE_OVERRIDE_FIRST_DAY_THIS_YEAR:
        return timezone.now().replace(day=1, month=1, hour=23, minute=59, tzinfo=tzinfo)

    if preset == TEST_DATE_OVERRIDE_OCTOBER_TENTH_THIS_YEAR:
        return timezone.now().replace(day=10, month=10, hour=9, minute=0, tzinfo=tzinfo)

    if preset == TEST_DATE_OVERRIDE_DECEMBER_FIFTEENTH_THIS_YEAR:
        return timezone.now().replace(day=15, month=12, hour=9, minute=0, tzinfo=tzinfo)

    if preset == TEST_DATE_OVERRIDE_LAST_MINUTE_OF_THIS_YEAR:
        return timezone.now().replace(
            day=31, month=12, hour=23, minute=59, tzinfo=tzinfo
        )

    if preset == TEST_DATE_OVERRIDE_END_OF_FIRST_DAY_NEXT_YEAR:
        return timezone.now().replace(
            day=1,
            month=1,
            hour=23,
            minute=59,
            year=timezone.now().year + 1,
            tzinfo=tzinfo,
        )

    LOG.error(f"Unknown test date override preset: '{preset}'")
    return timezone.now()


def format_subscription_list_html(subs):
    return f"{'<br/>'.join(map(lambda x: '- ' + x.long_str(), subs))}"


def legal_status_is_cooperative(cache):
    return (
        get_parameter_value(ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache)
        == LEGAL_STATUS_COOPERATIVE
    )


def legal_status_is_association(cache):
    return (
        get_parameter_value(ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache)
        == LEGAL_STATUS_ASSOCIATION
    )
