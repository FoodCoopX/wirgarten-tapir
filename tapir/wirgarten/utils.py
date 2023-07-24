from django.utils import timezone
import datetime
from decimal import Decimal
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from tapir.wirgarten.constants import Permission


def format_date(date: datetime.date) -> str:
    if date is None:
        return ""
    return f"{str(date.day).zfill(2)}.{str(date.month).zfill(2)}.{date.year}"


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


def get_today():
    return timezone.localdate()


def get_now():
    return timezone.now()
