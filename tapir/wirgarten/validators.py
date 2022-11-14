from datetime import date
from importlib.resources import _

from django.core.exceptions import ValidationError

from tapir.wirgarten.models import GrowingPeriod


def validate_growing_period_overlap(start_date: date, end_date: date):
    """
    Validates if the given start and end dates would overlap with and existing GrowingPeriod.

    :param start_date: the start date of the new growing period
    :param end_date: the end date of the new growing period
    """

    query = GrowingPeriod.objects.filter(
        start_date__lte=end_date, end_date__gte=start_date
    )
    if query.exists():
        colliding = query.first()
        raise ValidationError(
            f"{_('The growing periods must not overlap! Colliding period:')} {colliding.start_date} - {colliding.end_date}"
        )


def validate_date_range(start_date: date, end_date: date):
    """
    Validates if the given date range is valid.

    :param start_date: the start of the date range
    :param end_date: the end of a date range
    """

    if start_date > end_date:
        raise ValidationError(
            f"{_('The start date must be before the end date!')} start: {start_date}, end: {end_date}"
        )

    if start_date == end_date:
        raise ValidationError(
            f"{_('The start date must not be the same as the end date!')} start: {start_date}, end: {end_date}"
        )
