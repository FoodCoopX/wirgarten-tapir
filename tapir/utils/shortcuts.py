import calendar
import datetime
import os
from typing import Dict, Callable

from django.shortcuts import redirect
from django.utils import timezone
from django.utils.encoding import iri_to_uri
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect(redirect_url, default, request):
    if redirect_url is None:
        return redirect(default)

    if not url_has_allowed_host_and_scheme(
        url=redirect_url, allowed_hosts=None, require_https=request.is_secure()
    ):
        return redirect("/")

    url = iri_to_uri(redirect_url)
    return redirect(url)


def get_monday(date: datetime.date):
    return date - datetime.timedelta(days=date.weekday())


def week_to_monday(year: int, week: int) -> datetime.date:
    """Convert ISO year + week to the Monday of that week."""
    return datetime.date.fromisocalendar(year, week, 1)


def get_timezone_aware_datetime(
    date: datetime.date, time: datetime.time
) -> datetime.datetime:
    result = datetime.datetime.combine(date, time)
    return timezone.make_aware(result) if timezone.is_naive(result) else result


def get_from_cache_or_compute[T](
    cache: Dict | None, key, compute_function: Callable[[], T]
) -> T:
    if cache is None:
        return compute_function()
    return dict_get_or_set(cache, key, compute_function)


def dict_get_or_set(dictionary: Dict, key, call_if_not_set: callable):
    if key not in dictionary:
        dictionary[key] = call_if_not_set()
    return dictionary[key]


def get_first_of_next_month(date: datetime.date):
    return (date.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)


def get_last_day_of_month(date: datetime.date) -> datetime.date:
    return date.replace(day=calendar.monthrange(date.year, date.month)[1])


def is_running_tests():
    return "PYTEST_CURRENT_TEST" in os.environ


def get_serializer_cache(serializer) -> Dict:
    """
    The request-scoped cache dict a serializer should pass to TapirCache.

    Views that already build a cache put it in the serializer context. Without
    one, fall back to a cache per serializer instance, which is still a single
    cache for a whole many=True render because ListSerializer reuses one child
    instance for every item.
    """
    cache = serializer.context.get("cache")
    if cache is None:
        cache = serializer.__dict__.setdefault("_tapir_cache", {})
    return cache
