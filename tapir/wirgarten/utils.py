from zoneinfo import ZoneInfo
from django.utils import timezone
import datetime
from decimal import Decimal
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from tapir.wirgarten.constants import Permission


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


def get_today() -> datetime.date:
    return timezone.localdate()


def get_now() -> datetime.datetime:
    return timezone.now()
