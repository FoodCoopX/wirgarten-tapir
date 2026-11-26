import datetime

from django.utils import timezone


def make_timezone_aware(dt: datetime.datetime):
    return timezone.make_aware(dt) if timezone.is_naive(dt) else datetime
